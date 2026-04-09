# backend-development

Backend API design, database architecture, microservices patterns, and test-driven development.

## What it covers

A reference guide loaded on demand when designing APIs, database schemas, or backend system architecture. It does not expose a slash command — Claude consults it when backend design questions arise.

## Topics

- RESTful conventions — resource naming, HTTP verbs, nested routes
- Response and error envelope formats with pagination metadata
- Database schema design — UUID public IDs, soft deletes, indexing
- Query patterns — cursor pagination, efficient counting
- Authentication — JWT payload shape and middleware pattern
- Caching strategy — cache-aside reads and invalidation on writes
- Rate limiting — per-IP windowed limiter
- Observability — structured logging, metrics, tracing, health checks

## Source

Adapted from [wshobson/agents](https://github.com/wshobson/agents) (MIT).
