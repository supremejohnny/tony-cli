from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Iterator, Protocol

from .api_client import ApiClient, MessageRequest, StreamEvent
from .models import (
    ConversationMessage,
    Session,
    TextBlock,
    TokenUsage,
    ToolResultBlock,
    ToolUseBlock,
    UsageTracker,
)
from .permissions import PermissionMode, PermissionPolicy
from .tools import execute_tool, mvp_tool_specs


# ---------------------------------------------------------------------------
# ToolExecutor protocol
# ---------------------------------------------------------------------------

class ToolExecutor(Protocol):
    def execute(self, name: str, input: dict) -> str: ...  # noqa: A002


# ---------------------------------------------------------------------------
# CliToolExecutor
# ---------------------------------------------------------------------------

class CliToolExecutor:
    def __init__(self, policy: PermissionPolicy) -> None:
        self._policy = policy

    def execute(self, name: str, input: dict) -> str:  # noqa: A002
        mode = self._policy.authorize(name, input)
        if mode == PermissionMode.DENY:
            return f"Permission denied: tool '{name}' is not allowed in the current permission mode"
        return execute_tool(name, input)


# ---------------------------------------------------------------------------
# Message format conversion
# ---------------------------------------------------------------------------

def _to_api_messages(messages: list[ConversationMessage]) -> list[dict]:
    """Convert internal messages to Anthropic API format.

    Merges consecutive tool-result messages into the preceding user turn, as
    required by the Anthropic messages API (tool results must be in a user
    message's content array).
    """
    api_msgs: list[dict] = []

    for msg in messages:
        if msg.role == "tool":
            # Merge tool results into the last user message, or create one
            tool_blocks = [
                {"type": "tool_result", "tool_use_id": b.tool_use_id, "content": b.content}
                for b in msg.blocks
                if isinstance(b, ToolResultBlock)
            ]
            if api_msgs and api_msgs[-1]["role"] == "user":
                existing = api_msgs[-1]["content"]
                if isinstance(existing, list):
                    existing.extend(tool_blocks)
                else:
                    api_msgs[-1]["content"] = [{"type": "text", "text": existing}, *tool_blocks]
            else:
                api_msgs.append({"role": "user", "content": tool_blocks})
            continue

        if msg.role == "user":
            # Simple user message with text blocks
            parts = []
            for b in msg.blocks:
                if isinstance(b, TextBlock):
                    parts.append({"type": "text", "text": b.text})
            content: str | list = parts[0]["text"] if len(parts) == 1 else parts
            api_msgs.append({"role": "user", "content": content})

        elif msg.role == "assistant":
            parts = []
            for b in msg.blocks:
                if isinstance(b, TextBlock):
                    parts.append({"type": "text", "text": b.text})
                elif isinstance(b, ToolUseBlock):
                    parts.append({
                        "type": "tool_use",
                        "id": b.id,
                        "name": b.name,
                        "input": b.input,
                    })
            api_msgs.append({"role": "assistant", "content": parts})

    return api_msgs


# ---------------------------------------------------------------------------
# ConversationRuntime
# ---------------------------------------------------------------------------

@dataclass
class ConversationRuntime:
    session: Session
    api_client: ApiClient
    tool_executor: ToolExecutor
    permission_policy: PermissionPolicy
    model: str = "claude-sonnet-4-6"
    max_tokens: int = 8096
    max_iterations: int = 16
    usage_tracker: UsageTracker = field(default_factory=UsageTracker)
    system_blocks: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    def run_turn(self, user_input: str) -> Iterator[str]:
        """Process one user turn, yielding text chunks as they stream.

        Handles tool calls internally — loops until the model stops using tools
        or max_iterations is reached.
        """
        from .compressor import compact_session

        # Append user message
        self.session.messages.append(
            ConversationMessage(role="user", blocks=[TextBlock(text=user_input)])
        )

        tool_specs = mvp_tool_specs()
        tools_payload = [t.to_api_dict() for t in tool_specs]

        system_payload = [{"type": "text", "text": t} for t in self.system_blocks] if self.system_blocks else None

        for _iteration in range(self.max_iterations):
            # Compact if needed before each API call
            self.session = compact_session(self.session)

            req = MessageRequest(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=_to_api_messages(self.session.messages),
                system=system_payload,
                tools=tools_payload,
                stream=True,
            )

            # Stream and collect response
            text_chunks: list[str] = []
            tool_use_blocks: list[ToolUseBlock] = []
            stop_reason: str = "end_turn"
            input_tokens = 0
            output_tokens = 0

            # Track in-progress tool_use accumulation
            current_tool: dict | None = None
            current_tool_input_json: list[str] = []

            for event in self.api_client.stream_message(req):
                if event.type == "message_start":
                    usage = event.data.get("message", {}).get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)

                elif event.type == "content_block_start":
                    block = event.data.get("content_block", {})
                    if block.get("type") == "tool_use":
                        current_tool = {
                            "id": block.get("id", ""),
                            "name": block.get("name", ""),
                        }
                        current_tool_input_json = []

                elif event.type == "content_block_delta":
                    delta = event.data.get("delta", {})
                    delta_type = delta.get("type")
                    if delta_type == "text_delta":
                        chunk = delta.get("text", "")
                        text_chunks.append(chunk)
                        yield chunk
                    elif delta_type == "input_json_delta" and current_tool is not None:
                        current_tool_input_json.append(delta.get("partial_json", ""))

                elif event.type == "content_block_stop":
                    if current_tool is not None:
                        raw_json = "".join(current_tool_input_json)
                        try:
                            parsed_input = json.loads(raw_json) if raw_json else {}
                        except json.JSONDecodeError:
                            parsed_input = {"_raw": raw_json}
                        tool_use_blocks.append(ToolUseBlock(
                            id=current_tool["id"],
                            name=current_tool["name"],
                            input=parsed_input,
                        ))
                        current_tool = None
                        current_tool_input_json = []

                elif event.type == "message_delta":
                    stop_reason = event.data.get("delta", {}).get("stop_reason", "end_turn")
                    usage = event.data.get("usage", {})
                    output_tokens = usage.get("output_tokens", 0)

            # Track usage
            self.usage_tracker.add(TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            ))

            # Build assistant message blocks
            assistant_blocks = []
            if text_chunks:
                assistant_blocks.append(TextBlock(text="".join(text_chunks)))
            assistant_blocks.extend(tool_use_blocks)

            self.session.messages.append(
                ConversationMessage(role="assistant", blocks=assistant_blocks)
            )

            # If no tool calls, we're done
            if stop_reason != "tool_use" or not tool_use_blocks:
                break

            # Execute tools and append results
            tool_result_blocks: list[ToolResultBlock] = []
            for tub in tool_use_blocks:
                result = self.tool_executor.execute(tub.name, tub.input)
                tool_result_blocks.append(ToolResultBlock(
                    tool_use_id=tub.id,
                    content=result,
                ))
                # Yield a visual indicator that a tool ran
                yield f"\n[tool: {tub.name}]\n"

            self.session.messages.append(
                ConversationMessage(role="tool", blocks=tool_result_blocks)  # type: ignore[arg-type]
            )

        else:
            yield "\n[max_iterations reached]"
