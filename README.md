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

Custom agents invoked automatically by Claude based on task context.

| Agent | Model | Description |
|-------|-------|-------------|
| **code-griller** | Opus | Uncompromising code reviewer that catches every issue - bugs, security vulnerabilities, performance bottlenecks, and code smells. Perfect for pre-production reviews and critical components. |
| **elite-fullstack-architect** | Opus | Rapid full-stack development agent for building complete applications, complex architectures, and performance-critical implementations across any tech stack. |

## Commands

User-invocable slash commands. Type `/<name>` in Claude Code to run them.

### Git & Workflow

| Command | Usage | Description |
|---------|-------|-------------|
| **commit** | `/commit [message]` | Create git commit with conventional commit message format |
| **commit-all** | `/commit-all` | Create git commits in logical groups for all current changes |
| **pr** | `/pr [title]` | Commit pending changes, push, and create a pull request |
| **pr-fix** | `/pr-fix <url>` | Fix failing CI checks on a pull request |
| **issue** | `/issue <issue-id>` | Implement a Linear issue end-to-end |
| **hotfix** | `/hotfix <description>` | Emergency hotfix workflow for production issues |
| **release** | `/release [version] [branch] [pre-release]` | Create a GitHub release with auto-generated changelog |
| **orchestrate** | `/orchestrate <description>` | End-to-end feature workflow — branch, implement, review-fix, PR, wait, pr-fix |

### Development

| Command | Usage | Description |
|---------|-------|-------------|
| **build** | `/build [target]` | Build project (auto-detects: Gradle, Maven, Cargo, npm/yarn/pnpm, Go, Make, CMake, Python, Ruby, Elixir, Zig, Deno, Bun, PHP/Composer, Docker) |
| **install** | `/install [--device <target>] [--variant <variant>]` | Install the app on a device, emulator, or simulator (auto-detects platform) |
| **run** | `/run [--no-install] [--device <target>] [--variant <variant>]` | Build, install, and launch the app on a target device |
| **cmp** | `/cmp <cmd> [args]` | Run docker compose commands (e.g., `/cmp up -d`, `/cmp logs -f`) |
| **implement** | `/implement <feature>` | Full TDD implementation of a feature with review cycles |
| **refactor** | `/refactor <target>` | Safe refactoring with comprehensive test coverage |

### Code Quality

| Command | Usage | Description |
|---------|-------|-------------|
| **review** | `/review` | Thorough code review of current branch against main using code-griller |
| **review-fix** | `/review-fix [cycles]` | Review code and fix issues in iterative cycles |
| **cleanup** | `/cleanup [module\|all]` | Find and remove dead code, unused imports, and technical debt |
| **debug** | `/debug <error>` | Debug and fix failing tests or errors |
| **investigate** | `/investigate <issue>` | Deep investigation of bugs, performance issues, or unexpected behavior |

### Maintenance

| Command | Usage | Description |
|---------|-------|-------------|
| **update-claudes** | `/update-claudes` | Pull latest commands/skills/agents from repo and verify symlinks are in sync |
| **history?** | `/history? <query>` | Search Claude Code conversation history on disk for a given query |

## Skills

Reference guides loaded by Claude on demand. These are not user-invocable — Claude consults them when relevant context appears.

| Skill | Description |
|-------|-------------|
| **backend-development** | Backend API design, database architecture, microservices patterns, TDD |
| **database-design** | Schema design, optimization, migrations for PostgreSQL, MySQL, NoSQL |
| **frontend-design** | Create distinctive, production-grade UIs that avoid generic AI aesthetics |
| **react-best-practices** | React hooks, component patterns, state management, performance optimization |
| **swoole-expert** | Deep reference for Swoole PHP (5.x/6.x) — coroutines, hooks, servers, pooling, pitfalls |

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
