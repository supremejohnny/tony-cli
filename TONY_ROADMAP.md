# Tony CLI — Rust Port Roadmap

_Based on: claw-code/rust trajectory + tony-cli/rust unique extensions_
_Last updated: 2026-04-05_

---

## Current State

### Existing crates

| Crate | Status | Notes |
|-------|--------|-------|
| `api` | Working | Anthropic HTTP client + SSE streaming |
| `commands` | Working | Slash command metadata and parsing |
| `compat-harness` | Working | Compatibility layer |
| `runtime` | Working | Session loop, config, permissions, compaction |
| `plugins` | Working | Plugin system |
| `tools` | Working | Built-in tool implementations |
| `claw-cli` | **Skeleton** | Main binary — only `/help`, `/status`, `/compact` |
| `lsp` | **Skeleton** | LSP client (tony-only) |
| `server` | **Skeleton** | HTTP session server with SSE push (tony-only) |

### Gap vs claw-code

- **Slash commands**: claw-code has ~30 working commands; tony has 3
- **Mock test harness**: claw-code has `mock-anthropic-service` + 10 end-to-end scenarios; tony has none
- **TUI**: rendering layers are comparable, but claw-code has a detailed improvement plan underway
- **Tony's unique advantage**: `server` (HTTP REST + SSE) and `lsp` — claw-code has neither

---

## Phase 0 — Slash Command Parity

**Goal**: Make `claw-cli` usable day-to-day.

Port commands from claw-code's `handle_repl_command` in priority order.

### P0 — Immediately useful

| Command | Description |
|---------|-------------|
| `/model <name>` | Switch model (opus / sonnet / haiku) |
| `/cost` | Show token usage and cost estimate for current session |
| `/clear` | Clear current session |
| `/permissions <mode>` | Switch permission mode (read-only / workspace-write / danger-full-access) |

### P1 — Session management

| Command | Description |
|---------|-------------|
| `/session list` | List past sessions |
| `/session switch <id>` | Switch to a session |
| `/session fork` | Fork the current session |
| `/resume <id>` | Resume a past session |
| `/export <path>` | Export session as JSON or Markdown |

### P2 — Information and tooling

| Command | Description |
|---------|-------------|
| `/diff` | Show current git diff |
| `/memory` | Display memory file contents |
| `/config [section]` | Inspect current configuration |
| `/mcp list / show` | MCP server management |
| `/plugin list / install / enable / disable` | Plugin management |

### P3 — Workflow acceleration

| Command | Description |
|---------|-------------|
| `/commit` | Auto-generate and execute a git commit |
| `/pr` | Auto-generate a PR description and open it |
| `/issue` | Create a GitHub issue |
| `/bughunter` | Automated bug-hunt mode |
| `/ultraplan` | Deep task planning |
| `/doctor` | Environment self-check report |

---

## Phase 1 — Mock Parity Harness

**Goal**: Deterministic end-to-end testing without a real API key.

Modelled on claw-code's `mock-anthropic-service` + `rusty-claude-cli/tests/mock_parity_harness.rs`.

### New crates / files needed

- **`mock-anthropic-service` crate**: spins up a fake `/v1/messages` HTTP server returning scripted SSE responses
- **`claw-cli/tests/mock_parity_harness.rs`**: runs scenarios against a clean workspace and isolated environment

### Scenario coverage order

1. `streaming_text` — basic streaming text output
2. `read_file_roundtrip` — file read tool round-trip
3. `write_file_allowed` / `write_file_denied` — write permission enforcement
4. `grep_chunk_assembly` — grep result chunk assembly
5. `bash_stdout_roundtrip` — bash execution output
6. `bash_permission_prompt_approved` / `denied` — bash permission prompt flows
7. `multi_tool_turn_roundtrip` — multiple tools in a single turn
8. `plugin_tool_roundtrip` — plugin tool execution path

---

## Phase 2 — TUI Enhancements

**Goal**: Better daily-use experience. Follows claw-code's `TUI-ENHANCEMENT-PLAN.md`.

### 2.1 Structural cleanup (prerequisite)

`claw-cli/src/main.rs` will grow quickly as Phase 0 commands land. Extract before it becomes painful:

```
claw-cli/src/
├── main.rs          # Entry point + arg dispatch only (<150 lines)
├── args.rs          # Already exists — complete it
├── app.rs           # Already exists — LiveCli struct + REPL loop
├── format.rs        # Extract: status, cost, model formatting helpers
├── session_mgr.rs   # Extract: session CRUD
├── input.rs         # Already exists — extend tab completion
├── render.rs        # Already exists — extend
└── tui/
    ├── status_bar.rs  # Persistent bottom status line
    ├── tool_panel.rs  # Tool call visualization
    └── diff_view.rs   # Colored diff rendering
```

### 2.2 Status bar (high value, moderate effort)

- Fixed bottom line: model name, permission mode, session ID, cumulative tokens, estimated cost
- Real-time update: refresh on every `AssistantEvent::Usage` event during streaming
- Terminal-width-aware via `crossterm::terminal::size()`

### 2.3 Streaming output improvements

- Remove the 8 ms artificial per-chunk delay
- Collapse tool results longer than N lines behind a `[+] expand` hint
- Show colored unified diff when `edit_file` succeeds

### 2.4 Color themes

- Dark (current default) / Light / Solarized
- Wire into the existing `theme` field in `Config`

---

## Phase 3 — Tony-Specific Extensions

This is where tony diverges from claw-code and builds its own identity.

### 3.1 HTTP Server — complete the skeleton

The `server` crate already has axum + SSE routing, but `send_message` only stores the message in memory — it does not invoke the AI runtime.

**Completion targets:**

- `POST /sessions/{id}/message` triggers the `runtime` conversation loop and pushes streamed events over SSE
- Session persistence to disk (survives restarts)
- API key authentication middleware
- Enables web frontends, VS Code extensions, or scripts to drive tony over HTTP

### 3.2 LSP Client — complete the skeleton

The `lsp` crate has `client`, `manager`, and `types` modules. Wiring it into `runtime` lets the AI:

- Read diagnostics (errors, warnings) from any running language server
- Request hover info, go-to-definition, references, completions
- Trigger formatting after file edits

**vs. claw-code**: claw-code exposes LSP as a runtime tool that the AI calls on demand. Tony's `lsp` crate is a separate layer that can be integrated deeper — for example, automatically injecting current-file diagnostics into every conversation turn via the `server` layer.

### 3.3 Server + LSP integration

End state:

```
tony server start
  └─ connects to local LSP server (rust-analyzer / pyright / tsserver)
  └─ listens on HTTP /sessions
  └─ on each user message → attaches workspace LSP diagnostics
                          → runs AI conversation loop
                          → streams events back over SSE
```

This turns tony into an embeddable local AI programming backend, not just a CLI tool.

---

## Milestone summary

| Phase | Goal | Prerequisite | Deliverable |
|-------|------|-------------|-------------|
| **0** | Slash command parity with claw-code | — | tony usable day-to-day |
| **1** | Mock parity harness | Phase 0 partially done | Test without API key |
| **2** | TUI enhancements | Phase 0 complete | Better UX |
| **3.1** | HTTP server complete | Phase 0 | tony as local AI service |
| **3.2** | LSP client complete | Phase 0 | AI-aware code diagnostics |
| **3.3** | Server + LSP integration | Phase 3.1 + 3.2 | Embeddable AI backend |

---

## Development principles

1. **Phase 0 first**: nothing else matters until basic slash commands work
2. **Mock before real**: write a harness scenario before implementing a feature
3. **Port, don't reinvent**: if claw-code already has it working, port it — save energy for the server/lsp differentiation
4. **Refactor follows growth**: don't split modules preemptively; extract when `main.rs` actually becomes hard to navigate
