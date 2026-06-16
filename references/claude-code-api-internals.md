# Claude Code API Call Internals

What Claude Code sends to the LLM on each API call, and how to intercept it.

## What's in an API Call

Each POST to `/v1/messages` contains:

### 1. System Prompt (dynamically assembled)

Built from ~8 always-included sections + conditionals. Key sections (from dbreunig.com
analysis of the leaked source):

| Section | Content |
|---------|---------|
| Intro | "You are an interactive agent that helps users with software engineering tasks..." |
| System Rules | Tool use, permissions, prompt injection, context compression |
| Doing Tasks | Read before editing, minimal changes, no over-engineering |
| Executing Actions with Care | Blast radius, reversibility, check with user for risky actions |
| Using Your Tools | Prefer dedicated tools (Read/Edit/Glob/Grep) over raw bash |
| Tone and Style | No emojis, cite file paths, GitHub link format |
| Output Efficiency | Be concise (external users especially) |
| Summarize Tool Results | Note important info since tool results may be cleared |

**Conditional additions** (included when applicable):
- Custom output styles (if `output_style` is set)
- Tool-specific guidance (AskUserQuestion, Shell shortcuts)
- MCP tool schemas (if MCP servers connected)
- CLAUDE.md project context (if present in working directory)
- Skills/Slash commands (loaded skills, their tool definitions)
- Thinking budget config
- Permission mode config
- Session-specific instructions (from hooks, custom instructions)

### 2. Messages Array

The full conversation history:
- User messages (text content)
- Assistant responses (text + tool_use blocks)
- Tool results (tool_result blocks, including errors from denied tools)

### 3. Tool Definitions (JSON schemas)

Available tools registered by the agent harness:
- Read, Write, Edit, Glob, Grep (file operations)
- Bash (shell execution)
- Task, TaskOutput (subagent delegation)
- WebSearch, WebFetch (web access)
- NotebookEdit (Jupyter)
- AskUserQuestion (user interaction)
- Plus any MCP tools and skill-defined tools

### 4. Model Config

- `model`: requested model ID (e.g., `claude-opus-4-8`)
- `max_tokens`: output token cap
- `thinking`: budget/type for extended thinking
- `temperature`
- `system`: the assembled system prompt
- `metadata`: user_id, session attribution

## Interception Options

### Option 1: cc-switch Log (metadata only)

```
~/.cc-switch/logs/cc-switch.log
```

Format: `[timestamp][INFO][cc_switch_lib::proxy::forwarder] [Claude] >>> 请求 URL: https://api.moonshot.ai/v1/chat/completions (model=kimi-k2.6)`

Shows: timestamp, upstream URL, mapped model. Does NOT show request body.

The cc-switch DB at `~/.cc-switch/cc-switch.db` stores config/settings, not request logs.

### Option 2: Claude Code --debug (metadata + timing)

```bash
claude -p "query" --debug --debug-file /tmp/debug.log
claude -p "query" --debug api  # filter by category
```

Key lines in debug output:
- `[API:request] Creating client, ANTHROPIC_CUSTOM_HEADERS present: false`
- `[API:timing] dispatching to firstParty model=claude-opus-4-8`
- `[API REQUEST] /v1/messages source=sdk`
- `[API:timing] first byte after 5435ms`

Does NOT show request body content.

Debug env vars attempted without success: `DEBUG=1`, `DEBUG_SDK=1` (no additional body logging observed with v2.1.177).

### Option 3: Modify cc-switch (full body)

The cc-switch Rust proxy already parses the full request body in
`map_proxy_request_model()` (`src-tauri/src/claude_desktop_config.rs:681`).
It has to — it rewrites the model name and normalizes thinking history.

Adding one `log::info!("{}", body)` line there would dump the complete
Anthropic-format request (system prompt + messages + tools + model config)
to `~/.cc-switch/logs/cc-switch.log` on every call.

The cc-switch binary is at `~/cc-switch/src-tauri/target/release/cc-switch`.
Recompile takes ~2 minutes. The proxy auto-starts via bash profile.

## The Agent Loop (architectural context)

From the claw-code Rust rewrite analysis:

```
def run_turn(user_input):
    session.messages.append(UserMessage(user_input))
    while True:
        response = api_client.stream(system_prompt, session.messages)
        assistant_message = parse_response(response)
        session.messages.append(assistant_message)
        tool_calls = extract_tool_uses(assistant_message)
        if not tool_calls:
            break  # model decided to respond, not call tools
        for tool_name, input in tool_calls:
            result = tool_executor.execute(tool_name, input)
            session.messages.append(ToolResult(result))
```

Key insight: the agent loop continues calling the LLM until the model
responds with text (no more tool calls). A single "turn" from the user's
perspective may be 2-10+ API calls depending on tool use.

## Session Storage

Claude Code 2.x stores sessions as `.jsonl` files:
```
~/.claude/projects/<project-path-hash>/<session-id>.jsonl
```

Each line is a JSON event (user message, assistant response, tool use, tool result).
This is the source of truth for conversation state — the messages array in each
API call is reconstructed from this file.
