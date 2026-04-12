---
name: docker-expert
description: House rules and load-bearing patterns for Docker, Docker Compose, and container orchestration. Covers multi-stage build patterns (PHP+Swoole compile-in-builder, copy-to-runtime), BuildKit features (cache mounts, secret mounts, heredoc syntax, multi-platform with buildx), image optimization (base image selection, layer ordering, .dockerignore), Swoole-specific container patterns (compiling from source vs pecl, PHP ini tuning for long-running processes, opcache for Swoole), PID 1 and signal handling (tini, graceful shutdown), Docker Compose service orchestration (healthcheck-gated depends_on, volume strategies, network config, profiles, watch mode, override files), security hardening (non-root, read-only filesystems, capability dropping, image scanning), networking, volume patterns, logging, resource limits, container debugging, registry patterns, CI/CD, and anti-patterns. Does NOT cover basic Docker concepts, elementary CLI commands, or installation. Use when writing or reviewing Dockerfiles, Compose files, or container infrastructure.
---

# Docker Expert

Reference for Docker, Docker Compose, and container best practices. **Assumes baseline Docker knowledge** (images, containers, basic Dockerfile, basic CLI, elementary Compose). Only what's house-specific, load-bearing, or shifts year-to-year.

Non-negotiable defaults:
- **Multi-stage builds always.** Builder compiles, runtime copies artifacts.
- **BuildKit enabled.** `# syntax=docker/dockerfile:1` at the top of every Dockerfile.
- **Non-root runtime.** Every production container runs as a non-root user.
- **No secrets in image layers.** `--mount=type=secret`, never `ENV`/`COPY` for credentials.
- **Healthchecks on every long-running service.** `depends_on` with `condition: service_healthy`.
- **Pin base image tags.** `php:8.3-cli-bookworm`, never `php:latest`. Use `@sha256:...` in CI.

---

## 1. Multi-stage builds

### 1.1 PHP + Swoole pattern

```dockerfile
# syntax=docker/dockerfile:1
FROM php:8.3-cli-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev libcurl4-openssl-dev libssl-dev libsqlite3-dev zlib1g-dev \
    && docker-php-ext-install -j$(nproc) pdo_mysql pdo_pgsql pdo_sqlite sockets \
    && pecl install swoole \
    && docker-php-ext-enable swoole \
    && rm -rf /var/lib/apt/lists/*

FROM php:8.3-cli-bookworm AS runtime
COPY --from=builder /usr/local/lib/php/extensions/ /usr/local/lib/php/extensions/
COPY --from=builder /usr/local/etc/php/conf.d/ /usr/local/etc/php/conf.d/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libpq.so* /usr/lib/x86_64-linux-gnu/
COPY --from=builder /usr/lib/x86_64-linux-gnu/libsqlite3.so* /usr/lib/x86_64-linux-gnu/
COPY --chown=appwrite:appwrite . /app
WORKDIR /app
USER appwrite
ENTRYPOINT ["php", "server.php"]
```

- Copy the extensions **directory**, not individual `.so` files -- survives version bumps.
- Copy shared lib `.so*` glob -- catches symlinks (`libpq.so.5 -> libpq.so.5.17`).
- `--chown` on COPY -- avoids a separate `chown` layer.

### 1.2 Swoole source compile (when custom flags needed)

```dockerfile
ARG SWOOLE_VERSION=6.0.0
RUN apt-get update && apt-get install -y --no-install-recommends \
        libcurl4-openssl-dev libssl-dev libpq-dev libsqlite3-dev liburing-dev \
    && cd /tmp \
    && curl -fSL "https://github.com/swoole/swoole-src/archive/v${SWOOLE_VERSION}.tar.gz" | tar xz \
    && cd "swoole-src-${SWOOLE_VERSION}" \
    && phpize && ./configure \
        --enable-openssl --enable-swoole-curl --enable-swoole-pgsql \
        --enable-swoole-sqlite --enable-sockets \
    && make -j$(nproc) && make install \
    && docker-php-ext-enable swoole
```

Use `pecl install swoole` for standard builds. Source compile only for `--enable-swoole-curl`, `--enable-iouring`, etc.

### 1.3 Layer ordering for cache efficiency

```dockerfile
# Order: base packages (monthly) -> extensions (monthly) -> deps (weekly) -> code (every commit)
COPY composer.json composer.lock ./
RUN --mount=type=cache,target=/root/.composer/cache \
    composer install --no-dev --prefer-dist --no-scripts --no-autoloader
COPY . .
RUN composer dump-autoload --optimize --classmap-authoritative
```

---

## 2. BuildKit features

### 2.1 Cache mounts

```dockerfile
RUN --mount=type=cache,target=/root/.composer/cache \
    composer install --no-dev --prefer-dist                # composer cache survives across builds

RUN --mount=type=cache,target=/var/cache/apt \
    --mount=type=cache,target=/var/lib/apt/lists \
    apt-get update && apt-get install -y --no-install-recommends libpq-dev

RUN --mount=type=cache,target=/tmp/pear \
    pecl install swoole                                    # pecl download cache
```

### 2.2 Secret and SSH mounts

```dockerfile
RUN --mount=type=secret,id=composer_auth,target=/root/.composer/auth.json \
    composer install --no-dev --prefer-dist
# Build: docker build --secret id=composer_auth,src=auth.json .

RUN --mount=type=ssh \
    git clone git@github.com:acme/private-lib.git /tmp/lib
# Build: docker build --ssh default .
```

`ARG`/`ENV` for tokens persist in image metadata (`docker inspect`). Secret mounts exist only during `RUN`.

### 2.3 Heredoc syntax and multi-platform

```dockerfile
RUN <<EOF
apt-get update
apt-get install -y --no-install-recommends libpq-dev
rm -rf /var/lib/apt/lists/*
EOF

COPY <<EOF /usr/local/etc/php/conf.d/swoole.ini
[swoole]
swoole.use_shortname = Off
EOF
```

```bash
docker buildx create --name multiarch --driver docker-container --use
docker buildx build --platform linux/amd64,linux/arm64 --tag registry.example.com/app:1.0.0 --push .
```

Platform-specific logic: use `ARG TARGETARCH` then `case "${TARGETARCH}" in amd64) ... ;; arm64) ... ;; esac`.

---

## 3. Image optimization

| Base | Size | Use when |
|---|---|---|
| `php:8.3-cli-bookworm` | ~490 MB | Builder stage |
| `php:8.3-cli-alpine` | ~80 MB | Small runtime, all deps in apk |
| Bookworm slimmed via multi-stage | ~150 MB | Runtime needs glibc (some extensions break on musl) |

**Alpine caveats**: musl libc (intl/gd may need extra flags), DNS `ndots:5` in k8s causes 5x queries (set `ndots:1`), no glibc locale support.

**Rule**: Debian Bookworm for builder. Alpine or multi-stage-slimmed Bookworm for runtime.

### .dockerignore (always have one)

```gitignore
.git
.github
.idea
.vscode
*.md
docker-compose*.yml
Dockerfile*
.env*
node_modules
vendor
tests
storage/logs/*
storage/cache/*
```

### Layer minimization

- Combine `RUN` with `&&` -- each `RUN` = one layer.
- Clean up in the **same** `RUN`: `apt-get install && rm -rf /var/lib/apt/lists/*`. Separate cleanup layer doesn't reduce size.
- `--no-install-recommends` with apt. `COPY --link` for parallel layer processing.

---

## 4. PHP ini and opcache for Swoole containers

```ini
; appwrite.ini -- long-running process settings
max_execution_time = 0          ; Swoole workers run indefinitely
memory_limit = 512M             ; per worker, not per request (worker_num * limit <= container memory)
max_input_time = -1             ; Swoole manages lifecycle
post_max_size = 128M
upload_max_filesize = 128M
display_errors = Off
log_errors = On
error_reporting = E_ALL
error_log = /dev/stderr
```

```ini
; opcache.ini -- CRITICAL settings for Swoole
opcache.enable = 1
opcache.enable_cli = 1
opcache.validate_timestamps = 0         ; files don't change at runtime; reload workers for updates
opcache.preload = /app/preload.php      ; hot classes shared across workers
opcache.preload_user = appwrite
opcache.memory_consumption = 256
opcache.interned_strings_buffer = 32
opcache.max_accelerated_files = 30000
opcache.jit = 1255                      ; profile-guided for Swoole hot paths
opcache.jit_buffer_size = 128M
```

For development: `validate_timestamps=1` or file watch + `$server->reload()`.

---

## 5. Signal handling, PID 1, and healthchecks

### PID 1 problem

PID 1 in a container: no default signal handlers (SIGTERM ignored), must reap zombie children.

**Solution: tini** (preferred):

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends tini
ENTRYPOINT ["tini", "--"]
CMD ["php", "server.php"]
```

Or Compose `init: true`. Swoole signal handlers (`Process::signal(SIGTERM, ...)`) work but don't reap zombies.

### Graceful shutdown

```yaml
services:
  app:
    stop_grace_period: 30s  # must be >= swoole max_wait_time; SIGKILL after expiry
```

Sequence: SIGTERM -> tini forwards -> Swoole master signals workers -> workers drain -> exit.

### Healthchecks

```dockerfile
# HTTP server -- TCP or curl
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8080/health || exit 1
```

```php
// Worker/queue containers (no port) -- file-based heartbeat
file_put_contents('/tmp/heartbeat', (string) time());  // in worker loop
```

```dockerfile
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD php -r "exit(time() - (int)file_get_contents('/tmp/heartbeat') > 60 ? 1 : 0);"
```

---

## 6. Docker Compose orchestration

### 6.1 Healthcheck-gated dependencies

```yaml
services:
  mariadb:
    image: mariadb:11
    healthcheck:
      test: ["CMD", "healthcheck.sh", "--connect", "--innodb_initialized"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    volumes:
      - mariadb-data:/var/lib/mysql

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 3

  app:
    build: .
    depends_on:
      mariadb:
        condition: service_healthy   # NEVER bare depends_on -- waits for start, not ready
      redis:
        condition: service_healthy
```

### 6.2 Volume strategies

| Type | Use when |
|---|---|
| Named (`mariadb-data:/var/lib/mysql`) | Persistent data, databases |
| Bind (`./src:/app/src:cached`) | Dev hot-reload (`:cached` for macOS perf) |
| tmpfs (`tmpfs: /tmp:size=100M`) | Ephemeral scratch, runtime secrets |
| Anonymous (`/var/lib/mysql` no name) | **Never** -- can't reference or clean up |

**Permissions gotcha**: root-created files in container = root on host bind mount. Fix: `user: "${UID}:${GID}"` in Compose, or use named volumes.

### 6.3 Environment variables

```yaml
services:
  app:
    env_file:
      - .env              # base config
      - .env.local        # local overrides (gitignored)
    environment:
      APP_ENV: production # highest precedence
```

Precedence (high to low): `environment:` > shell env > `env_file:` (later files override earlier) > Dockerfile `ENV`. Never `env_file` for production secrets -- use Docker secrets or a vault.

### 6.4 Override files

```yaml
# docker-compose.yml -- shared base
# docker-compose.override.yml -- dev (auto-loaded: build context, bind mounts, debug flags)
# docker-compose.prod.yml -- production (replicas, resource limits, log rotation)
```

```bash
docker compose up                                                    # dev (auto-loads override)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d  # prod
```

### 6.5 Profiles and watch mode

```yaml
services:
  app:
    profiles: []          # always starts
  maildev:
    image: maildev/maildev
    profiles: ["dev"]
  prometheus:
    image: prom/prometheus
    profiles: ["monitoring"]

  app:
    develop:
      watch:
        - action: sync              # hot copy files
          path: ./src
          target: /app/src
        - action: rebuild           # full rebuild on lockfile change
          path: ./composer.lock
        - action: sync+restart      # copy then restart container
          path: ./config
          target: /app/config
```

```bash
docker compose --profile dev up
docker compose watch          # or: docker compose up --watch
```

### 6.6 Networks

```yaml
services:
  app:
    networks: [frontend, backend]
  mariadb:
    networks: [backend]           # not accessible from frontend
  traefik:
    networks: [frontend]
    ports: ["80:80", "443:443"]

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true                # no outbound internet
```

Services on same user-defined bridge resolve by service name (Docker DNS). Default bridge has **no** DNS -- always create named networks.

---

## 7. Networking

| Mode | When |
|---|---|
| `bridge` (default) | Standard isolation, DNS by service name |
| `host` | Max network perf, binding many ports |
| `none` | Batch jobs, volume-only access |
| `container:<name>` | Sidecar pattern, shared network namespace |

```yaml
ports:
  - "8080:80"              # published to host
  - "127.0.0.1:3306:3306"  # localhost only
expose:
  - "9000"                 # inter-service only, not host
```

`ports` publishes externally; `expose` does not. Use `expose` for inter-service, `ports` for external.

Round-robin DNS for scaled services: `docker compose up --scale app=3` resolves all under `app`.

---

## 8. Security

```dockerfile
# Non-root user (Debian)
RUN groupadd -r appwrite && useradd -r -g appwrite -d /app -s /sbin/nologin appwrite
COPY --chown=appwrite:appwrite . /app
USER appwrite

# Alpine variant
RUN addgroup -S appwrite && adduser -S appwrite -G appwrite -h /app -s /sbin/nologin
```

```yaml
services:
  app:
    read_only: true                  # read-only root filesystem
    tmpfs:
      - /tmp:size=100M              # writable scratch
    volumes:
      - uploads:/app/storage/uploads # writable named volume for persistent data
    cap_drop: [ALL]
    cap_add: [NET_BIND_SERVICE]      # only if port < 1024
    security_opt: [no-new-privileges:true]
```

### Image scanning

```bash
trivy image --exit-code 1 --severity HIGH,CRITICAL registry.example.com/app:latest  # CI gate
grype registry.example.com/app:latest                                                # alternative
```

---

## 9. Resource limits and logging

### Resources

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          memory: 1G      # OOM-killed if exceeded
          cpus: "2.0"
        reservations:
          memory: 512M
          cpus: "1.0"
    ulimits:
      nofile:
        soft: 65535       # Swoole needs high fd limit for concurrent connections
        hard: 65535       # default 1024 is far too low
```

**Memory budget**: `worker_num * memory_limit + master overhead + buffer`. 4 workers * 512M + 200M = ~2.3G limit.

### Logging

```dockerfile
ENV SWOOLE_LOG_FILE=/dev/stderr   # never write logs to container filesystem
```

```yaml
services:
  app:
    logging:
      driver: json-file
      options:
        max-size: "10m"           # default json-file has NO rotation -- disk fills up
        max-file: "3"
```

For log aggregators: `driver: fluentd` with `fluentd-address` and `tag`.

---

## 10. Container debugging

```bash
docker compose exec app bash                                        # shell into container (sh for Alpine)
docker compose logs -f --timestamps app                             # follow logs
docker stats --no-stream                                            # resource usage snapshot
docker inspect <id> --format '{{.State.ExitCode}} {{.State.Error}}' # why did it exit?

# Network debugging
docker compose exec app nslookup mariadb                            # DNS resolution
docker network inspect <name> | jq '.[0].Containers'               # network membership

# Advanced: nsenter (distroless images with no shell)
PID=$(docker inspect --format '{{.State.Pid}}' <id>)
nsenter -t $PID -n ss -tlnp                                        # listening sockets from host
```

---

## 11. Registry and CI/CD

### Tagging strategy

```bash
docker tag app:latest registry.example.com/app:1.5.2        # semver (immutable -- never overwrite)
docker tag app:latest registry.example.com/app:sha-abc1234  # git SHA for traceability
docker tag app:latest registry.example.com/app:latest       # convenience only, never deploy target
```

Always build `amd64` + `arm64` (Apple Silicon dev, Graviton/Ampere prod).

### GitHub Actions

```yaml
- uses: docker/setup-buildx-action@v3
- uses: docker/build-push-action@v6
  with:
    context: .
    platforms: linux/amd64,linux/arm64
    push: true
    tags: registry.example.com/app:${{ github.sha }}
    cache-from: type=gha
    cache-to: type=gha,mode=max       # caches all layers including intermediate stages
```

Registry cache for larger projects: `cache-from: type=registry,ref=...:buildcache`.

### Build once, promote

Build one image, push once, deploy the same SHA to staging/canary/production. Environment differences come from runtime config only. **Never rebuild per environment.**

### DinD vs socket mount

| Approach | Use when |
|---|---|
| DinD (`docker:dind`) | Full isolation; add persistent volume for `/var/lib/docker` to retain cache |
| Socket mount (`/var/run/docker.sock`) | Fast, shares host cache; security risk (full host Docker access) |
| Buildx remote driver | Best of both; more complex setup |
| `docker/build-push-action` (GHA) | Handles BuildKit automatically; no DinD or socket needed |

---

## 12. Anti-patterns

### Build

| About to write | Write instead | Why |
|---|---|---|
| Single-stage with build tools in runtime | Multi-stage: builder compiles, runtime copies | 3x image size, larger attack surface |
| `COPY . .` before `RUN composer install` | `COPY composer.json composer.lock ./` first | Code changes bust dependency cache |
| Separate `RUN apt-get update` and `RUN apt-get install` | One `RUN` with `&& rm -rf /var/lib/apt/lists/*` | Stale index; separate cleanup doesn't reduce size |
| `ADD https://example.com/file.tar.gz` | `RUN curl -fSL ... \| tar xz` | ADD can't use cache mounts, layer persists download |
| `ENV COMPOSER_AUTH={"token":"..."}` | `--mount=type=secret` | Secrets baked into image metadata |
| `FROM php:latest` | `FROM php:8.3-cli-bookworm` | Unpinned -- builds break without warning |
| Separate `RUN chown` after `COPY` | `COPY --chown=appwrite:appwrite` | Extra layer for ownership |

### Runtime

| About to write | Write instead | Why |
|---|---|---|
| Running as root | `USER appwrite` | Root in container = root on host if escape |
| `depends_on: [mariadb]` (bare) | `depends_on: { mariadb: { condition: service_healthy } }` | Started != ready; race condition |
| Logging to `/var/log/app.log` | stdout/stderr + log driver | Lost on restart, fills overlay |
| No resource limits | `deploy.resources.limits` | OOM container takes down host |
| `restart: always` without healthcheck | `restart: unless-stopped` + healthcheck | Crash loop burns CPU undetected |
| State in container filesystem | Named volumes (persistent) or tmpfs (ephemeral) | Container replacement = data loss |
| Default bridge network | Named networks | No DNS, no segmentation |
| `composer update` in running container | Rebuild the image | Not reproducible |

### Compose

| About to write | Write instead | Why |
|---|---|---|
| Hardcoded passwords in `docker-compose.yml` | `env_file` + `.env.local` (gitignored) or Docker secrets | Credentials in git |
| `volumes: [./vendor:/app/vendor]` | Named volume or don't mount | Wrong platform binaries; defeats caching |
| Anonymous volumes | Named volumes | Can't reference, backup, or clean up |
| `json-file` without rotation | Always set `max-size` and `max-file` | Disk fills over days |
| `network_mode: host` for convenience | Bridge with explicit port mapping | No isolation; port conflicts |
| `version: "3.8"` at top | Omit entirely | Deprecated since Compose v2; ignored |
