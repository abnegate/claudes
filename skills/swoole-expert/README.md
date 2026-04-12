# swoole-expert

Deep reference for writing production Swoole PHP code (swoole/swoole-src, **not** openswoole).

## What it covers

A comprehensive reference loaded on demand when writing or reviewing Swoole code. It does not expose a slash command — Claude consults it when Swoole-related work comes up.

## Topics

- The long-running process mental model — four object lifetimes, what breaks vs php-fpm (superglobals, `session_start`, `echo`, `exit`, `header`, static state)
- Coroutines — `go()`, `Co\run()`, cooperative scheduling, parent/child priority, introspection, cancellation, `setTimeLimit`
- Runtime hooks — every `SWOOLE_HOOK_*` flag including 6.2 additions (`PDO_FIREBIRD`, `MONGODB`, `NET_FUNCTION`), what's not hookable
- Concurrency primitives — `Channel`, `WaitGroup`, `Barrier`, `defer`, `batch`/`parallel`/`map`, `Timer`
- Servers — `Http\Server`, `WebSocket\Server`, TCP with packet framing, all events, `Request`/`Response` API, task workers, dispatch modes, graceful reload
- `Swoole\Process` and `Swoole\Process\Pool` — signal handling, IPC, when to use which
- Shared memory — `Table`, `Atomic`, `Lock` (and why `Lock` isn't coroutine-safe)
- Coroutine clients — `Http\Client`, `Http2\Client`, `Socket`, hooked PDO + curl (Guzzle works)
- Connection pooling — `ConnectionPool`, `PDOPool`, `RedisPool`, `MysqliPool`, channel-as-pool pattern, "put it back or leak" rule
- Pitfalls catalog — blocking inside coroutines, sharing connections, `pcntl_*`, deadlocks, cooperative ≠ concurrent-safe, exception handling, framework compatibility (Hyperf, Octane, etc.)
- Production tuning — `worker_num`, `max_request`, `reload_async`, buffers, dispatch modes, kernel sysctls
- Debugging — live introspection, Xdebug incompatibility, GDB with gdbinit
- Testing — PHPUnit entry point, state reset, `swoole/ide-helper`
- Swoole 6.x version notes — what's new/removed in 6.0, 6.1, 6.2, build flags, `swoole/library` version alignment

## Target

- Swoole 5.x / 6.x (upstream `swoole/swoole-src`, not openswoole)
- PHP 8.2+ (6.2 requires 8.2; 6.0/6.1 work on 8.1)

## Source

Compiled from upstream docs (`swoole/docs`), extension stubs (`ext-src/stubs/*.stub.php`), `swoole/library` source, GitHub release notes for v6.0.0–v6.2.0, and real-world patterns observed in the Appwrite codebase.
