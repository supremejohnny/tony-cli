from __future__ import annotations

import json

from .models import ConversationMessage, Session, TextBlock


def estimate_tokens(text: str) -> int:
    """Rough token estimate: 1 token ≈ 4 characters."""
    return len(text) // 4


def _message_token_estimate(msg: ConversationMessage) -> int:
    total = 0
    for block in msg.blocks:
        if isinstance(block, TextBlock):
            total += estimate_tokens(block.text)
        else:
            # ToolUseBlock / ToolResultBlock — serialize to JSON for estimation
            total += estimate_tokens(json.dumps(block.__dict__))
    return total


def compact_session(
    session: Session,
    threshold_tokens: int = 80_000,
    keep_last_n: int = 10,
) -> Session:
    """Trim old messages when the session exceeds threshold_tokens.

    Keeps the last `keep_last_n` messages and prepends a short summary
    message so the model retains some context about what happened earlier.
    Returns a new Session; does not mutate the original.
    """
    total = sum(_message_token_estimate(m) for m in session.messages)
    if total <= threshold_tokens:
        return session

    kept = session.messages[-keep_last_n:] if len(session.messages) > keep_last_n else session.messages
    dropped = len(session.messages) - len(kept)

    summary_msg = ConversationMessage(
        role="assistant",
        blocks=[TextBlock(
            text=(
                f"[Context compacted: {dropped} earlier message(s) removed to stay within token limits. "
                "The conversation continues from the most recent messages below.]"
            )
        )],
    )

    return Session(messages=[summary_msg, *kept])
