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

### Option 2: Symlink (local development)

Clone the repo and symlink into your Claude config — useful when iterating on the contents:

```bash
git clone git@github.com:abnegate/claudes.git ~/Local/claudes

ln -sf ~/Local/claudes/commands ~/.claude/commands
ln -sf ~/Local/claudes/skills ~/.claude/skills
ln -sf ~/Local/claudes/agents ~/.claude/agents
```

With symlinks, commands are invoked without the namespace prefix (`/commit`, `/pr`, ...).

## Agents

Specialized agents that form a structured execution cycle. The **orchestrator** is the entry point — it coordinates the others automatically for non-trivial tasks.

```
orchestrator
  -> planner        (decompose task into subtasks)
  -> verifier       (validate plan correctness + efficiency)
  -> architects     (parallel worktree execution)
  -> consolidator   (merge all branches)
  -> reviewer       (review merged output)
  -> verifier       (confirm acceptance criteria met)
```

| Agent | Model | Role |
|-------|-------|------|
| **orchestrator** | Opus | Conducts the full cycle — entry point for any non-trivial task |
| **planner** | Opus | Decomposes tasks into smallest work units, maps dependencies and parallelism |
| **verifier** | Opus | Validates plans pre-execution and confirms outcomes post-execution |
| **architect** | Opus | Implements code in worktree isolation — production-ready, any tech stack |
| **consolidator** | Opus | Merges parallel worktree branches with intelligent conflict resolution |
| **reviewer** | Opus | Reviews code for bugs, security, performance, readability, and maintainability |

## Commands

User-invocable slash commands. Type `/<name>` in Claude Code to run them.

### Git & Workflow

| Command | Usage | Description |
|---------|-------|-------------|
| **commit** | `/commit [message]` | Create git commit with conventional commit message |
| **commit-all** | `/commit-all` | Create git commits in logical groups for all current changes |
| **pr** | `/pr [title]` | Commit pending changes, push, and create a pull request |
| **pr-fix** | `/pr-fix <url>` | Fix failing CI checks and address PR comments |
| **issue** | `/issue <issue-id>` | Implement a Linear issue end-to-end using the orchestrator cycle |
| **hotfix** | `/hotfix <description>` | Emergency hotfix workflow for production issues |
| **release** | `/release [version] [branch]` | Create a GitHub release with auto-generated changelog |
| **orchestrate** | `/orchestrate <description>` | End-to-end feature workflow — branch, implement, improve, PR, wait, pr-fix |

### Development

| Command | Usage | Description |
|---------|-------|-------------|
| **implement** | `/implement <feature>` | TDD feature implementation via the orchestrator cycle |
| **refactor** | `/refactor <target>` | Safe refactoring with planner, parallel worktrees, and verification |
| **build** | `/build [target]` | Build project (auto-detects build system) |
| **install** | `/install [--device <target>]` | Install app on device/emulator (auto-detects platform) |
| **run** | `/run [--device <target>]` | Build, install, and launch app on target device |

### Code Quality

| Command | Usage | Description |
|---------|-------|-------------|
| **improve** | `/improve [cycles]` | Review and improve code — fix bugs, harden security, optimize performance, improve readability |
| **review** | `/review` | Read-only code review of current branch against main |
| **cleanup** | `/cleanup [module\|all]` | Remove dead code, unused imports, and technical debt |
| **debug** | `/debug <error>` | Debug and fix failing tests or errors |
| **investigate** | `/investigate <issue>` | Deep investigation of bugs, performance issues, or unexpected behavior |

### Utilities

| Command | Usage | Description |
|---------|-------|-------------|
| **history?** | `/history? <query>` | Search Claude Code conversation history on disk |
| **profile?** | `/profile?` | Build a developer profile from git activity and session history |

## Skills

Reference guides loaded by Claude on demand. These are not user-invocable — Claude consults them automatically when relevant context appears.

| Skill | Description |
|-------|-------------|
| **consolidation** | The full agent cycle — orchestrator, planner, verifier, architects, consolidator, reviewer |
| **android-expert** | Jetpack Compose + MVI house rules — contract pattern, Koin, Nav3, strong skipping, testing scaffold |
| **php-expert** | PHP 8.3+ house rules — typed constants, enums, exceptions, PHPUnit 12, Pint/PHPStan/Rector |
| **swoole-expert** | Swoole 5.x/6.x — coroutines, runtime hooks, servers, connection pooling, pitfalls, 6.x API changes |
| **backend-development** | Backend API design, database architecture, microservices patterns, TDD |
| **database-design** | Schema design, optimization, migrations for PostgreSQL, MySQL, NoSQL |
| **frontend-design** | Create distinctive, production-grade UIs that avoid generic AI aesthetics |
| **react-best-practices** | React hooks, component patterns, state management, performance optimization |

## Adding to Projects

To include this collection in a project's git repo, add as a submodule:

```bash
git submodule add git@github.com:abnegate/claudes.git .claude/claudes
```

Or copy specific commands:

```bash
cp ~/Local/claudes/commands/build.md .claude/commands/
```

## License

MIT
