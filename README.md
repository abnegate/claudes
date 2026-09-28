# Claudes

Personal Claude Code commands, skills, and agents for global use across all projects.

## Setup

### Option 1: Claude Code plugin (recommended)

Install via the built-in plugin marketplace:

```
/plugin marketplace add abnegate/claudes
/plugin install skills@claudes
```

Slash commands are namespaced under `skills:`, so they're invoked as `/skills:commit`, `/skills:pr`, etc.

### Option 2: Local development

Clone the repo and load the working tree — useful when iterating on the contents:

```bash
git clone git@github.com:abnegate/claudes.git ~/Local/claudes
claude --plugin-dir ~/Local/claudes
```

`claude --plugin-dir ~/Local/claudes` loads the working tree for one session and overrides the installed `skills@claudes`, so changes can be tried before they are published. Commands keep the `skills:` namespace.

Don't symlink `commands/`, `skills/` or `agents/` into a profile. The plugin already provides them, and `commands/*.md` are symlinks to `skills/*/SKILL.md`, so each workflow would register at least twice.

### Updating

Refresh the marketplace clone once, then update every profile:

1. Refresh the marketplace in the profile that owns the clone, `~/.claude`: `claude plugin marketplace update claudes`, or `env -u CLAUDE_CONFIG_DIR claude plugin marketplace update claudes` from a shell that exports another profile's `CLAUDE_CONFIG_DIR`.
2. Run `claude plugin update skills@claudes` in each profile. It updates the user-scope install by default; for a project install, add `--scope project` and run it from that project's directory. For a named profile, prefix the command with `CLAUDE_CONFIG_DIR=~/.claude-<profile>`.
3. Restart running sessions; an update applies on restart.

Profiles copied from `~/.claude` share its marketplace clone: their `known_marketplaces.json` points at `~/.claude/plugins/marketplaces/claudes` instead of a clone inside their own `plugins/marketplaces`. Claude Code reports that as a "corrupted installLocation", so `claude plugin marketplace update` fails in those profiles. `claude plugin update` still works there: it installs from the shared clone and warns that the marketplace was not refreshed.

## Agents

Specialized agents that form a structured execution cycle. The **consolidation** skill loads the cycle into the conducting agent's context. The **top-level conductor** (the user-facing session with the skill loaded) conducts by default, dispatching the **stage agents**: planner, verifier, architect, consolidator, reviewer. When the plan splits into independent workstreams, it delegates each one to a **workstream conductor** (the `conductor` agent), which runs the same cycle on its own `ws-<workstream>` integration branch and hands back a Workstream report. Agents spawned by stage agents are **helpers**.

```
[top-level conductor — consolidation skill loaded]
  -> planner        (decompose task into subtasks, optionally workstreams)
  -> verifier       (validate plan correctness + efficiency)
  -> architects     (parallel worktree execution)
     or conductors  (optional: one per workstream, each running this
                     whole cycle on its own ws-<workstream> branch)
  -> consolidator   (merge all branches)
  -> reviewer       (review merged output)
  -> verifier       (confirm acceptance criteria met)
```

| Agent | Model | Role |
|-------|-------|------|
| **planner** | Opus | Decomposes tasks into smallest work units, maps dependencies, parallelism and workstreams |
| **verifier** | Opus | Validates plans pre-execution and confirms outcomes post-execution |
| **architect** | Opus | Implements code in its own worktree — production-ready, any tech stack |
| **conductor** | Opus | Runs the whole cycle for one workstream and hands back a Workstream report |
| **consolidator** | Opus | Merges parallel worktree branches with intelligent conflict resolution |
| **reviewer** | Opus | Reviews code for bugs, security, performance, readability, and maintainability |

By default subagents nest up to depth 3 (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`) and at most 20 run at once across the whole session (`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`), so conductors split that concurrency budget and launch larger waves in batches. An agent without the `Agent` tool is at the depth limit and does its stage's work itself.

| Depth | Top-level-only run | Nested run |
|---|---|---|
| 0 | top-level conductor | top-level conductor |
| 1 | stage agents | workstream conductors |
| 2 | helpers | stage agents |
| 3 | — | helpers (leaf: no `Agent` tool) |

## Commands

User-invocable slash commands. Run them as `/skills:<name>` in Claude Code, for example `/skills:commit`; the Usage column omits the `skills:` prefix.

### Git & Workflow

| Command | Usage | Description |
|---------|-------|-------------|
| **commit** | `/commit [message]` | Create git commit with conventional commit message |
| **commit-all** | `/commit-all` | Create git commits in logical groups for all current changes |
| **pr** | `/pr [title]` | Commit pending changes, push, and create a pull request |
| **pr-fix** | `/pr-fix <url>` | Fix failing CI checks and address PR comments |
| **issue** | `/issue <issue-id>` | Implement a Linear issue end-to-end using the consolidation cycle |
| **hotfix** | `/hotfix <description>` | Emergency hotfix workflow for production issues |
| **release** | `/release [version] [branch]` | Create a GitHub release with grouped changelog |
| **orchestrate** | `/orchestrate <description>` | End-to-end feature workflow — branch, implement, improve, PR, wait, pr-fix |

### Development

| Command | Usage | Description |
|---------|-------|-------------|
| **implement** | `/implement <feature>` | TDD feature implementation via the consolidation cycle |
| **refactor** | `/refactor <target>` | Safe refactoring with planner, parallel worktrees, and verification |
| **build** | `/build [target]` | Build project (auto-detects build system) |
| **install** | `/install [--device <target>]` | Install app on device/emulator (auto-detects platform) |
| **run** | `/run [--device <target>]` | Build, install, and launch app on target device |

### Code Quality

| Command | Usage | Description |
|---------|-------|-------------|
| **improve** | `/improve [cycles]` | Review and fix code across 6 dimensions — security, performance, correctness, readability, maintainability, testing |
| **review** | `/review` | Read-only code review of current branch against main |
| **cleanup** | `/cleanup [module\|all]` | Remove dead code, unused imports, and technical debt |
| **debug** | `/debug <error>` | Debug and fix failing tests or errors |
| **investigate** | `/investigate <issue>` | Deep investigation of bugs, performance issues, or unexpected behavior |

### Utilities

| Command | Usage | Description |
|---------|-------|-------------|
| **continue** | `/continue [context]` | Pick up unfinished work from where the last session left off |
| **history** | `/history <query>` | Search Claude Code conversation history on disk |
| **profile** | `/profile` | Build a developer profile from git activity and session history |
| **readme** | `/readme` | Assess the codebase and update the README with any new or outdated information |

## Skills

Reference guides Claude loads automatically when relevant context appears. They can also be invoked directly as `/skills:<name>`.

| Skill | Description |
|-------|-------------|
| **consolidation** | The full orchestration cycle — loads planner → verifier → parallel architects (or workstream conductors) → consolidator → reviewer → verifier into the conducting agent's context |
| **kotlin-expert** | Kotlin 2.x/K2/KMP — K2 migration, context parameters and other 2.x features, KMP expect/actual, house naming rules |
| **android-expert** | Jetpack Compose + MVI house rules — contract pattern, Koin, Nav3, strong skipping, testing scaffold |
| **php-expert** | PHP 8.3+ house rules — typed constants, enums, exceptions, PHPUnit 12, Pint/PHPStan/Rector |
| **swoole-expert** | Swoole 5.x/6.x — coroutines, runtime hooks, servers, connection pooling, pitfalls, 6.x API changes |
| **docker-expert** | Swoole-specific Docker/Compose — PHP+Swoole multi-stage builds, opcache tuning, PID 1 + graceful shutdown, healthchecks, memory budgeting |
| **backend-development** | Backend API design, database architecture, microservices patterns, TDD |
| **database-design** | Schema design, optimization, migrations for PostgreSQL, MySQL, NoSQL |
| **frontend-design** | Create distinctive, production-grade UIs that avoid generic AI aesthetics |
| **react-best-practices** | React hooks, component patterns, state management, performance optimization |

## User Config

The `user/` directory contains personal configuration:

| File | Purpose |
|------|---------|
| `user/CLAUDE.md` | Source of truth for the global instructions: each profile's `CLAUDE.md` (`~/.claude/CLAUDE.md`, `~/.claude-<profile>/CLAUDE.md`) is a symlink to it |
| `user/settings.json` | Symlink pointing at `~/.claude/settings.json`, the default profile's settings (plugins, marketplaces, hooks); other profiles keep their own |

Link a profile's `CLAUDE.md` to the repo:

```bash
ln -sf ~/Local/claudes/user/CLAUDE.md ~/.claude/CLAUDE.md
ln -sf ~/Local/claudes/user/CLAUDE.md ~/.claude-work/CLAUDE.md
```

## Adding to Projects

To enable the plugin for everyone working on a repo, install it at project scope from the repo's directory:

```bash
claude plugin install skills@claudes --scope project
```

Or copy specific commands:

```bash
cp ~/Local/claudes/commands/build.md .claude/commands/
```

## Development

Validate the plugin and run the tests from the repo root:

```bash
claude plugin validate --strict .
claude plugin validate --strict .claude-plugin/plugin.json
claude plugin validate --strict skills
claude plugin validate --strict agents
claude plugin validate commands
claude --plugin-dir . plugin details skills
python3 -m unittest discover -s tests -v
```

`claude plugin validate commands` runs without `--strict` because it always warns that the `commands/` symlinks are not followed. `validate` does not check agent frontmatter keys; `plugin details` loads the working tree and lists every skill and agent it registers.

## License

MIT
