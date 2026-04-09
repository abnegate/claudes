---
description: Pull latest skills/agents and verify symlinks are in sync
---

# Update Claudes

Pull the latest changes from the claudes repo and verify symlinks are properly configured.

## Execution

1. **Pull latest changes**:
   ```bash
   cd ~/Local/claudes && git pull
   ```

2. **Verify symlinks exist and point correctly**:
   ```bash
   ls -la ~/.claude/skills ~/.claude/agents
   ```

   Expected:
   - `~/.claude/skills` → `~/Local/claudes/skills`
   - `~/.claude/agents` → `~/Local/claudes/agents`

3. **If symlinks are broken or missing**, recreate them:
   ```bash
   rm -rf ~/.claude/skills && ln -s ~/Local/claudes/skills ~/.claude/skills
   rm -rf ~/.claude/agents && ln -s ~/Local/claudes/agents ~/.claude/agents
   ```

4. **Report status**:
   - Show git log of recent changes pulled
   - Confirm symlinks are valid
   - List available skills and agents
