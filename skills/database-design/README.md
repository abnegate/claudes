# database-design

Database schema design, optimization, and migration patterns for PostgreSQL, MySQL, and NoSQL databases.

Reference material loaded by Claude when designing schemas, writing migrations, or optimizing queries. There is no slash command — the skill provides guidance that Claude applies in context.

## What it covers

- Schema design principles: normalization (1NF-3NF) and deliberate denormalization for read-heavy paths.
- Index design: B-tree, composite, partial, GIN, and covering indexes, plus queries for analyzing index usage and finding missing indexes.
- Migration patterns: transactional templates, `CREATE INDEX CONCURRENTLY`, batched backfills, and a five-step zero-downtime column rollout.
- Query optimization: reading `EXPLAIN ANALYZE` output, `EXISTS` vs `IN`, keyset pagination, and CTE usage.
- Constraints and data integrity: primary keys, foreign keys with cascade, check, unique, and exclusion constraints.
- Best practices: UUIDs for public IDs, timestamp columns, soft deletes, and testing migrations against production-size data.

## Source

Adapted from [wshobson/agents](https://github.com/wshobson/agents) (MIT).
