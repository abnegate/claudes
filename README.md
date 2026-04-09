# Claudes

Personal Claude Code skills and agents for global use across all projects.

## Setup

Clone this repo and symlink to your Claude config:

```bash
git clone git@github.com:abnegate/claudes.git ~/Local/claudes

# Symlink to Claude config
ln -sf ~/Local/claudes/skills ~/.claude/skills
ln -sf ~/Local/claudes/agents ~/.claude/agents
```

## Agents

Custom agents invoked automatically by Claude based on task context.

| Agent | Model | Description |
|-------|-------|-------------|
| **code-griller** | Opus | Uncompromising code reviewer that catches every issue - bugs, security vulnerabilities, performance bottlenecks, and code smells. Perfect for pre-production reviews and critical components. |
| **elite-fullstack-architect** | Opus | Rapid full-stack development agent for building complete applications, complex architectures, and performance-critical implementations across any tech stack. |

## Skills

Skills are invoked with `/<skill-name>` in Claude Code.

### Git & Workflow

| Skill | Usage | Description |
|-------|-------|-------------|
| **commit** | `/commit [message]` | Create git commit with conventional commit message format |
| **commit-all** | `/commit-all` | Create git commits in logical groups for all current changes |
| **pr** | `/pr [title]` | Commit pending changes, push, and create a pull request |
| **pr-fix** | `/pr-fix <url>` | Fix failing CI checks on a pull request |
| **issue** | `/issue <issue-id>` | Implement a Linear issue end-to-end |
| **hotfix** | `/hotfix <description>` | Emergency hotfix workflow for production issues |
| **release** | `/release [version] [branch] [pre-release]` | Create a GitHub release with auto-generated changelog |
| **orchestrate** | `/orchestrate <description>` | End-to-end feature workflow — branch, implement, review-fix, PR, wait, pr-fix |

### Development

| Skill | Usage | Description |
|-------|-------|-------------|
| **build** | `/build [target]` | Build project (auto-detects: Gradle, Maven, Cargo, npm/yarn/pnpm, Go, Make, CMake, Python, Ruby, Elixir, Zig, Deno, Bun, PHP/Composer, Docker) |
| **install** | `/install [--device <target>] [--variant <variant>]` | Install the app on a device, emulator, or simulator (auto-detects platform) |
| **run** | `/run [--no-install] [--device <target>] [--variant <variant>]` | Build, install, and launch the app on a target device |
| **cmp** | `/cmp <cmd> [args]` | Run docker compose commands (e.g., `/cmp up -d`, `/cmp logs -f`) |
| **implement** | `/implement <feature>` | Full TDD implementation of a feature with review cycles |
| **refactor** | `/refactor <target>` | Safe refactoring with comprehensive test coverage |

### Code Quality

| Skill | Usage | Description |
|-------|-------|-------------|
| **review** | `/review` | Thorough code review of current branch against main using code-griller |
| **review-fix** | `/review-fix [cycles]` | Review code and fix issues in iterative cycles |
| **cleanup** | `/cleanup [module\|all]` | Find and remove dead code, unused imports, and technical debt |
| **debug** | `/debug <error>` | Debug and fix failing tests or errors |
| **investigate** | `/investigate <issue>` | Deep investigation of bugs, performance issues, or unexpected behavior |

### Reference Guides

| Skill | Description |
|-------|-------------|
| **backend-development** | Backend API design, database architecture, microservices patterns, TDD |
| **database-design** | Schema design, optimization, migrations for PostgreSQL, MySQL, NoSQL |
| **frontend-design** | Create distinctive, production-grade UIs that avoid generic AI aesthetics |
| **react-best-practices** | React hooks, component patterns, state management, performance optimization |

### Maintenance

| Skill | Usage | Description |
|-------|-------|-------------|
| **update-claudes** | `/update-claudes` | Pull latest skills/agents from repo and verify symlinks are in sync |
| **history** | `/history <query>` | Search Claude Code conversation history on disk for a given query |

## Adding to Projects

To include specific skills in a project's git repo, add as a submodule:

```bash
git submodule add git@github.com:abnegate/claudes.git .claude/claudes
```

Or copy specific skills:

```bash
cp -r ~/Local/claudes/skills/build .claude/skills/
```

## License

MIT
