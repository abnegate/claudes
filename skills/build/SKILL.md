---
name: build
description: Build the project (auto-detects build system)
argument-hint: "[target]"
disable-model-invocation: false
allowed-tools: Bash, Read, Glob
---

# Build Project

Build the project using the detected build system.

## Arguments

- `$ARGUMENTS` - Optional build target or arguments to pass to the build command

## Build System Detection

Detect the build system by checking for these files in order:

| File | Build System | Build Command | Test Command |
|------|--------------|---------------|--------------|
| `build.gradle.kts` | Gradle (Kotlin DSL) | `./gradlew build` | `./gradlew test` |
| `build.gradle` | Gradle (Groovy) | `./gradlew build` | `./gradlew test` |
| `pom.xml` | Maven | `mvn package` | `mvn test` |
| `Cargo.toml` | Cargo (Rust) | `cargo build` | `cargo test` |
| `package.json` | Node.js | `<pm> run build` | `<pm> test` |
| `go.mod` | Go | `go build ./...` | `go test ./...` |
| `Makefile` | Make | `make` | `make test` |
| `CMakeLists.txt` | CMake | `cmake --build .` | `ctest` |
| `setup.py` / `pyproject.toml` | Python | `pip install -e .` | `pytest` |
| `Gemfile` | Ruby | `bundle install` | `bundle exec rake test` |
| `mix.exs` | Elixir | `mix compile` | `mix test` |
| `build.zig` | Zig | `zig build` | `zig build test` |
| `deno.json` | Deno | `deno task build` | `deno test` |
| `bun.lockb` | Bun | `bun run build` | `bun test` |
| `composer.json` | PHP (Composer) | `composer install` | `composer test` or `./vendor/bin/phpunit` |
| `compose.yaml` / `docker-compose.yml` | Docker Compose | `docker compose build` | `docker compose run --rm test` |
| `Dockerfile` | Docker | `docker build -t <image> .` | N/A |

## Execution

1. **Detect**: Check for build files in project root
2. **Report**: Tell user which build system was detected
3. **Build**: Run the appropriate build command
   - If `$ARGUMENTS` provided, append to build command or use as target
4. **Verify**: Run tests after successful build
5. **Report**: Show build status, any errors, and summary

### Node.js Specifics

For Node.js projects, first detect the package manager (`<pm>` in table above):

1. **Check for lock files** (in order of priority):
   - `bun.lockb` → use `bun`
   - `pnpm-lock.yaml` → use `pnpm`
   - `yarn.lock` → use `yarn`
   - Otherwise → use `npm`

2. **Check `package.json` scripts**:
   - If `build` script exists: `<pm> run build`
   - If `build` script doesn't exist but it's a TypeScript project: `<pm> exec tsc` or `npx tsc`

### Gradle Specifics

- Use `./gradlew` wrapper if present, otherwise `gradle`
- For multi-module projects, `./gradlew build` builds all modules

### Rust Specifics

- Use `--release` flag for production builds: `cargo build --release`
- If `$ARGUMENTS` is "release", build in release mode

### PHP Specifics

For PHP projects with `composer.json`:

1. **Install dependencies**: `composer install`
2. **Run tests**:
   - If `test` script exists in `composer.json` scripts: `composer test`
   - Otherwise, check for PHPUnit: `./vendor/bin/phpunit`
   - Or PHPStan for static analysis: `./vendor/bin/phpstan analyse`
3. **Build** (if applicable):
   - If `build` script exists: `composer run build`
   - Laravel: `php artisan optimize`
   - Symfony: `php bin/console cache:clear`

### Docker Specifics

**Docker Compose** (preferred when present):

1. **Check for compose files** (in order):
   - `compose.yaml` (modern standard)
   - `compose.yml`
   - `docker-compose.yaml`
   - `docker-compose.yml`

2. **Build**: `docker compose build $ARGUMENTS`
   - Arguments passed directly (e.g., `/build --no-cache`, `/build api`)

3. **Run tests** (if test service exists): `docker compose run --rm test`

**Dockerfile only** (no compose file):

1. **Determine image name**: Use directory name as default tag

2. **Build**: `docker build -t <dirname> . $ARGUMENTS`
   - Arguments passed directly (e.g., `/build --no-cache`, `/build -f Dockerfile.dev`)
   - If multiple Dockerfiles exist, ask user which to build (unless `-f` specified)

## Test Failures

**IMPORTANT:** If any tests fail during or after the build, fix them. There is no such thing as a "pre-existing" test failure - all test failures must be resolved before the task is considered complete. The task always completes with completely passing tests.

## Error Handling

If build fails:
1. Read the error output carefully
2. Identify the root cause
3. Fix the issue
4. Re-run the build
5. Repeat until build succeeds

If no build system detected:
- Report to user that no recognized build system was found
- List the files checked
- Ask user how to build the project
