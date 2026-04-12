# docker-expert

House rules and load-bearing patterns for Docker, Docker Compose, and container orchestration. **Assumes baseline Docker knowledge** -- this skill only covers what's house-specific, what's load-bearing, or what shifts year-to-year.

## What it covers

- **Multi-stage builds** -- PHP+Swoole compile-in-builder, copy-to-runtime pattern; Swoole from source vs pecl; layer ordering for cache efficiency
- **BuildKit features** -- cache mounts (composer, apt, pecl), secret mounts, SSH mounts, heredoc syntax, multi-platform builds with buildx
- **Image optimization** -- base image selection (Alpine vs Bookworm vs distroless), .dockerignore, minimizing layers, `COPY --link`
- **PHP ini for Swoole containers** -- `max_execution_time=0`, memory limits per worker, opcache with `validate_timestamps=0`, JIT settings, preloading
- **PID 1 and signal handling** -- the problem, tini/dumb-init, Swoole signal registration, graceful shutdown sequence, `stop_grace_period`
- **Healthchecks** -- TCP/HTTP checks for Swoole servers, file-based heartbeat for worker containers
- **Docker Compose orchestration** -- healthcheck-gated `depends_on`, volume strategies (named/bind/tmpfs), environment variable precedence, override files for dev/prod, profiles, watch mode (Compose 2.22+), network configuration
- **Networking** -- bridge vs host vs none, DNS resolution rules, port mapping vs expose, internal networks
- **Security** -- non-root users (Debian and Alpine), read-only filesystems, capability dropping, image scanning with Trivy/Grype
- **Resource limits** -- memory budgeting for Swoole workers, CPU limits, ulimits (nofile for high-concurrency Swoole)
- **Logging** -- stdout/stderr only, log drivers, rotation settings, aggregator integration
- **Container debugging** -- exec, logs, inspect, network debugging, nsenter for distroless images
- **Registry and tagging** -- semver + SHA + latest strategy, immutable tags, multi-arch manifests
- **CI/CD** -- GitHub Actions with layer caching (GHA and registry), build-once-promote pattern, DinD vs socket mount vs buildx remote
- **Anti-patterns** -- build, runtime, and Compose mistakes to refuse on sight

## What it does NOT cover

Deliberately omitted because it's already in the training data:

- Basic Docker concepts (what a container/image is)
- Elementary Dockerfile instructions (FROM, RUN, COPY, CMD basics)
- Basic CLI commands (docker run, docker ps, docker stop)
- Basic Compose syntax at the introductory level
- Installation instructions

Runtime-specific patterns (Swoole coroutines, servers, channels, pools) live in `swoole-expert`. PHP language patterns live in `php-expert`.

## Target

- Docker Engine 24+ with BuildKit
- Docker Compose v2 (the `docker compose` plugin, not standalone `docker-compose`)
- Primary use case: PHP 8.3+ / Swoole 6 containers in the Appwrite ecosystem
- Patterns apply broadly to any multi-service containerized application

## Source

Compiled from Docker official documentation, BuildKit release notes, Docker Compose specification, real-world patterns from the Appwrite codebase, and production container experience with PHP/Swoole workloads.
