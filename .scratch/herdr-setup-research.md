# Herdr Research — Primary Source Findings

Research date: 2026-09-14  
Sources: Official https://herdr.dev documentation and https://github.com/herdrdev/herdr

---

## Pane Splitting

- **CLI command for splitting:** `herdr pane split [<pane_id>] --direction right|down [--ratio FLOAT]` — splits a pane in the specified direction; omitting `<pane_id>` uses the UI-focused pane, `--current` splits the calling pane. ([https://herdr.dev/docs/cli-reference](https://herdr.dev/docs/cli-reference))

- **Keyboard shortcuts:** `prefix+v` for splitting right, `prefix+minus` for splitting down. Default prefix is `ctrl+b`. ([https://herdr.dev/docs/quick-start](https://herdr.dev/docs/quick-start))

- **Mouse interaction:** Right-click within a pane to access context menus with splitting options; drag split borders to resize. ([https://herdr.dev/docs/quick-start](https://herdr.dev/docs/quick-start))

- **Pane definition:** A pane is "a real terminal" that Herdr renders, sends input to, and preserves across client detach. ([https://herdr.dev/docs/concepts](https://herdr.dev/docs/concepts))

- **Panes can be split right or down.** The documentation emphasizes both keyboard and mouse-based interaction are supported. ([https://herdr.dev/docs/concepts](https://herdr.dev/docs/concepts))

---

## Running Ordinary Shell Commands Within Herdr

- **Starting Herdr:** Simply run `herdr` from any project directory; Herdr automatically launches or connects to your default background session. ([https://herdr.dev/docs/quick-start](https://herdr.dev/docs/quick-start))

- **Typing commands in panes:** Start coding agents directly by typing commands like `claude`, `codex`, `pi`, or `opencode` in a pane; Herdr detects them automatically. ([https://herdr.dev/docs/quick-start](https://herdr.dev/docs/quick-start))

- **Sending text to panes:**
  - `herdr pane send-text` — sends raw text without automatic Enter ([https://herdr.dev/docs/cli-reference](https://herdr.dev/docs/cli-reference))
  - `herdr pane send-keys` — sends logical keys such as `enter`, `ctrl+c`, or `tab`; supports modifiers and special/function keys ([https://herdr.dev/docs/cli-reference](https://herdr.dev/docs/cli-reference))
  - `herdr pane run` — submits commands with Enter atomically, honoring live bracketed-paste mode ([https://herdr.dev/docs/cli-reference](https://herdr.dev/docs/cli-reference))

- **Key syntax for send-keys:** Supports modifiers (`ctrl+h`), special keys (`tab`, `esc`, `enter`), and function keys (`f1`). ([https://herdr.dev/docs/cli-reference](https://herdr.dev/docs/cli-reference))

- **Pane persistence:** When you detach with `ctrl+b q`, "the Herdr server keeps running" along with all panes, shells, and processes. Non-agent commands continue executing in the background. ([https://herdr.dev/docs/session-state](https://herdr.dev/docs/session-state))

---

## Keeping Focus / Attention Between Panes and Agents

- **Pane focus command:** `herdr pane focus --direction` navigates between panes in the specified direction. ([https://herdr.dev/docs/cli-reference](https://herdr.dev/docs/cli-reference))

- **Zoom panes:** `herdr pane zoom` toggles pane zoom state to focus on a single pane. ([https://herdr.dev/docs/cli-reference](https://herdr.dev/docs/cli-reference))

- **Higher-level focus:** `herdr workspace focus` and `herdr tab focus` allow switching contexts at workspace or tab level. ([https://herdr.dev/docs/cli-reference](https://herdr.dev/docs/cli-reference))

- **Status visibility in sidebar:** The sidebar aggregates agent status upward through the interface. A blocked agent makes its pane, tab, and workspace appear blocked; working agents highlight active workspaces. This creates the workflow: "start several agents, let them work in parallel, and use the sidebar to see which project needs a decision." ([https://herdr.dev/docs/agents](https://herdr.dev/docs/agents))

- **Agent status tracking:** Each pane has one status authority that determines whether the agent needs attention. Status is tracked as idle, working, or blocked. ([https://herdr.dev/docs/agents](https://herdr.dev/docs/agents))

- **Direct attachment:** Users can attach directly to individual agents using `herdr agent attach reviewer`, bypassing the UI for focused work. ([https://herdr.dev/docs/agents](https://herdr.dev/docs/agents))

---

## Agent Delegation / Task Coordination Between Agents and Panes

- **Socket API for control:** Herdr's Socket API uses "newline-delimited JSON over a local socket" and exposes methods organized by domain (workspace, tab, pane, agent, etc.). ([https://herdr.dev/docs/socket-api](https://herdr.dev/docs/socket-api))

- **Socket pane methods include:**
  - Layout operations: `pane.split`, `pane.swap`, `pane.move`, `pane.zoom`
  - Input/output: `pane.send_text`, `pane.send_keys`, `pane.read`
  - Navigation: `pane.focus`, `pane.resize`, `pane.neighbor`
  - Monitoring: `pane.process_info`, `pane.wait_for_output`
  
  ([https://herdr.dev/docs/socket-api](https://herdr.dev/docs/socket-api))

- **Agent communication:** Agents report state through `"$HERDR_BIN_PATH" pane report-agent "$HERDR_PANE_ID" --source custom:my-agent --agent my-agent --state working`. State values include `idle`, `working`, and `blocked`. ([https://herdr.dev/docs/integrations](https://herdr.dev/docs/integrations))

- **CLI and Socket equivalence:** "The entire Herdr CLI is the plugin API. Every command in the CLI reference is available to a plugin." Agents can also use the socket API directly via `HERDR_SOCKET_PATH`. ([https://herdr.dev/docs/plugins](https://herdr.dev/docs/plugins))

- **Agent coordination:** Agents can "split panes, start each other, prompt each other" through the CLI and socket API. ([https://herdr.dev/docs](https://herdr.dev))

- **Session restoration:** Native Agent Session Restore allows supported AI agents to resume conversations using official integration session references. This works automatically after server restarts for compatible tools like Claude Code, GitHub Copilot CLI, and others. ([https://herdr.dev/docs/session-state](https://herdr.dev/docs/session-state))

---

## HERDR_ENV Environment Variable

- **Purpose:** Marks that code is running within a Herdr environment. Value is set to `1`. ([https://herdr.dev/docs/socket-api](https://herdr.dev/docs/socket-api))

- **When set:** Injected by Herdr into all managed processes, signaling to agents and scripts that they are operating within Herdr. ([https://herdr.dev/docs/socket-api](https://herdr.dev/docs/socket-api))

- **Integration behavior:** Custom integrations should report agent state only when `HERDR_ENV=1` and required variables exist, ensuring they remain inactive outside Herdr. ([https://herdr.dev/docs/integrations](https://herdr.dev/docs/integrations))

- **Related injected variables:** Herdr also injects:
  - `HERDR_PANE_ID` — the current pane identifier
  - `HERDR_BIN_PATH` — path to the Herdr binary
  - `HERDR_SOCKET_PATH` — location of the control socket
  - `HERDR_WORKSPACE_ID`, `HERDR_TAB_ID` — resource identifiers
  
  ([https://herdr.dev/docs/socket-api](https://herdr.dev/docs/socket-api), [https://herdr.dev/docs/integrations](https://herdr.dev/docs/integrations))

- **Plugin context variables:** For plugins, Herdr also injects `HERDR_PLUGIN_ID`, `HERDR_PLUGIN_ROOT`, `HERDR_PLUGIN_CONFIG_DIR`, `HERDR_PLUGIN_STATE_DIR`, and `HERDR_PLUGIN_CONTEXT_JSON`. ([https://herdr.dev/docs/plugins](https://herdr.dev/docs/plugins))

---

## Configuration / Setup

### Installation

- **Primary method (macOS/Linux):** `curl -fsSL https://herdr.dev/install.sh | sh` ([https://herdr.dev/docs/install](https://herdr.dev/docs/install))

- **Windows:** PowerShell command or Command Prompt with curl to download and run installer script. ([https://herdr.dev/docs/install](https://herdr.dev/docs/install))

- **Alternative package managers:**
  - Homebrew: `brew install herdr`
  - Mise: `mise use -g herdr`
  - Nix: Using flakes with `nix run` or `nix profile install`
  
  ([https://herdr.dev/docs/install](https://herdr.dev/docs/install))

- **Manual installation:** Download binaries from GitHub releases for your architecture (Linux x86_64/aarch64, macOS Intel/Apple silicon, Windows). On Unix, make the binary executable and place on PATH. ([https://herdr.dev/docs/install](https://herdr.dev/docs/install))

### Configuration Files & Options

- **Configuration file location:**
  - Linux/macOS: `~/.config/herdr/config.toml`
  - Windows: `%APPDATA%\herdr\config.toml`
  
  ([https://herdr.dev/docs/configuration](https://herdr.dev/docs/configuration))

- **Keybindings configuration:** "Herdr has a prefix mode similar to tmux. The default prefix is `ctrl+b`." Configure keybindings with explicit syntax like `prefix+n` or direct shortcuts like `ctrl+alt+n`. Support for arrays (multiple shortcuts per action) and custom command keybindings with types `popup`, `pane`, `shell`, or `plugin_action`. ([https://herdr.dev/docs/configuration](https://herdr.dev/docs/configuration))

- **Configuration categories:**
  - Terminal defaults (shell executable, shell mode, working directory policy)
  - Keybindings (prefix mode, custom commands, indexed jumps)
  - Theme (built-in themes with auto-switching, custom color overrides)
  - UI elements (sidebar layouts, tab bar positioning, status areas, window titles)
  - Notifications and sound (delivery methods, custom audio files)
  - Advanced settings (scrollback limits, graphics rendering, session restoration)
  
  ([https://herdr.dev/docs/configuration](https://herdr.dev/docs/configuration))

### Environment Variables (Runtime)

Herdr recognizes several environment variables that can be set before launching:

- `HERDR_CONFIG_PATH` — Override default config file location
- `HERDR_SESSION` — Connect to a specific session
- `HERDR_SOCKET_PATH` — Socket location
- `HERDR_PROCESS_DETECTION` — Control process detection behavior
- `HERDR_LOG` — Enable logging
- `HERDR_DISABLE_SOUND` — Disable notifications/sounds

([https://herdr.dev/docs/configuration](https://herdr.dev/docs/configuration), [https://herdr.dev/docs/socket-api](https://herdr.dev/docs/socket-api))

### Initial Startup

- **First run:** Simply type `herdr` from any project directory. Herdr automatically launches or connects to the default background session with no manual socket management required. ([https://herdr.dev/docs/quick-start](https://herdr.dev/docs/quick-start))

- **Server management:** Detach from sessions with `ctrl+b q` while server and agents continue running. Stop sessions with `herdr server stop`. Manage separate runtime namespaces with `herdr session list` and `herdr session attach [name]`. ([https://herdr.dev/docs/concepts](https://herdr.dev/docs/concepts))

---

## Suggested AGENTS.md Additions

### Environment Detection
- Agents running in Herdr can detect the environment via the `HERDR_ENV=1` environment variable.
- When `HERDR_ENV=1`, agents have access to: `HERDR_PANE_ID`, `HERDR_BIN_PATH`, `HERDR_SOCKET_PATH`, `HERDR_WORKSPACE_ID`, `HERDR_TAB_ID`.

### Running Commands in Herdr
- Use `herdr pane send-text` to send raw text to a pane.
- Use `herdr pane send-keys` for logical keys (e.g., `enter`, `ctrl+c`, `tab`).
- Use `herdr pane run` to submit commands atomically with Enter.
- Use `herdr pane split --direction right|down` to create new panes for parallel work.

### Focus & Attention Management
- Use `herdr pane focus --direction` to navigate between panes.
- Use `herdr pane zoom` to toggle zoom on the current pane.
- Use `herdr workspace focus` and `herdr tab focus` to switch higher-level contexts.
- Herdr's sidebar aggregates agent status (idle, working, blocked) to highlight which project needs attention.

### Agent-to-Agent Coordination
- Report agent state with: `"$HERDR_BIN_PATH" pane report-agent "$HERDR_PANE_ID" --source custom:my-agent --agent my-agent --state <idle|working|blocked>`
- Access the full Socket API at `HERDR_SOCKET_PATH` for programmatic pane control, including `pane.split`, `pane.send_text`, `pane.focus`, `pane.wait_for_output`, and more.
- Agents can spawn sibling agents in new panes and coordinate via the Socket API or CLI.

### Configuration
- Config file at `~/.config/herdr/config.toml` (Linux/macOS) or `%APPDATA%\herdr\config.toml` (Windows).
- Default prefix key is `ctrl+b`; override in config.
- Common shortcuts: `prefix+v` (split right), `prefix+minus` (split down), `ctrl+b q` (detach).
- Override environment with: `HERDR_CONFIG_PATH`, `HERDR_SESSION`, `HERDR_SOCKET_PATH`, `HERDR_LOG`, `HERDR_DISABLE_SOUND`.

---

## Coverage Summary

All six requested topics have primary-source documentation:
1. ✅ **Pane Splitting** — Documented in CLI reference and quick-start.
2. ✅ **Running Ordinary Commands** — Documented in quick-start and CLI reference (send-text, send-keys, run).
3. ✅ **Keeping Focus** — Documented in CLI reference and agents guide (pane focus, zoom, status aggregation).
4. ✅ **Agent Delegation** — Documented in socket API, agents, and integrations guides.
5. ✅ **HERDR_ENV** — Documented in socket API and integrations guides.
6. ✅ **Config/Setup** — Documented in install, configuration, and quick-start guides.

No topics lacked primary-source coverage.
