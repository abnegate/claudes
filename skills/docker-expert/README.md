# docker-expert

Swoole-specific Docker patterns and house rules. **Assumes full Docker knowledge** -- only covers what's house-specific, Swoole-specific, or non-obvious. General Docker best practices (BuildKit features, image optimization, networking, security hardening, logging, debugging, CI/CD) are omitted as training-redundant.

## What it covers

- **PHP+Swoole multi-stage builds** -- pecl and source compile patterns, extension directory copying, shared lib glob copying
- **Layer ordering** -- composer cache mount, dependency-before-code ordering
- **PHP ini for Swoole** -- `max_execution_time=0`, per-worker memory limits, opcache with `validate_timestamps=0`, JIT settings, preloading
- **PID 1 + tini** -- signal forwarding, zombie reaping, graceful shutdown with `stop_grace_period >= max_wait_time`
- **Healthchecks** -- HTTP checks for servers, file-based heartbeat for worker/queue containers
- **Compose house patterns** -- healthcheck-gated `depends_on` (mariadb/redis example), watch mode, profiles
- **Swoole resource limits** -- memory budget formula (`worker_num * memory_limit`), ulimits nofile for fd-heavy workloads
- **Anti-patterns** -- Swoole-specific and non-obvious mistakes to refuse on sight

## What it does NOT cover

Deliberately omitted because it's well-covered in training data:

- BuildKit features (cache mounts, secret mounts, heredoc, multi-platform)
- Image optimization (base image selection, .dockerignore, layer minimization)
- Docker networking (bridge/host/none, DNS resolution, port mapping)
- Security hardening (non-root users, cap_drop, read-only filesystems, image scanning)
- Logging drivers and rotation
- Container debugging commands
- Registry tagging, CI/CD, GitHub Actions, DinD vs socket mount
- Basic Docker and Compose concepts

Runtime-specific patterns (Swoole coroutines, servers, channels, pools) live in `swoole-expert`. PHP language patterns live in `php-expert`.

## Target

- Docker Engine 24+ with BuildKit
- Docker Compose v2 (the `docker compose` plugin)
- Primary use case: PHP 8.3+ / Swoole 6 containers in the Appwrite ecosystem
