---
description: Run docker compose commands
argument-hint: "<command> [args]"
allowed-tools: Bash
---

# Docker Compose

Run `docker compose` with the provided arguments.

## Usage

```
/cmp <command> [args]
```

## Examples

- `/cmp up -d` → `docker compose up -d`
- `/cmp down` → `docker compose down`
- `/cmp logs -f api` → `docker compose logs -f api`
- `/cmp exec web bash` → `docker compose exec web bash`
- `/cmp ps` → `docker compose ps`
- `/cmp build --no-cache` → `docker compose build --no-cache`

## Execution

Run: `docker compose $ARGUMENTS`

If no arguments provided, run `docker compose ps` to show running services.
