---
description: Search Claude Code conversation history on disk for a given query. Use when the user asks to find something from a previous conversation, check what was discussed before, or recover lost context.
---

# Search Conversation History

Search through Claude Code conversation history JSONL files for the given query.

## Instructions

1. Identify the project history directory. For the current working directory, the history path is:
   `~/.claude/projects/<project-key>/.history/`
   
   The project key is derived from the working directory path with slashes replaced by dashes. For example:
   - `/Users/jakebarnby/Local/sshoo` → `-Users-jakebarnby-Local-sshoo`
   
   List `.history/*.jsonl` files sorted by modification time (newest first):
   ```bash
   ls -t ~/.claude/projects/<project-key>/.history/*.jsonl
   ```

2. Search the JSONL files for the user's query using grep:
   ```bash
   grep -l "<query>" ~/.claude/projects/<project-key>/.history/*.jsonl
   ```
   
   Then for matching files, extract surrounding context:
   ```bash
   grep -C 2 "<query>" <file> | head -100
   ```

3. Parse and present results:
   - Show which session file(s) matched
   - Show the relevant conversation context around each match
   - If the query relates to code, try to extract the actual code blocks
   - Summarize findings concisely

4. **For every matching session, output a resume command.** The session ID is the JSONL filename without the extension. Format:
   ```
   claude --dangerously-skip-permissions --resume <session-id>
   ```
   
   For example, if the matching file is `8afa50e5.jsonl`, output:
   ```
   claude --resume 8afa50e5
   ```
   
   List these at the end of the output grouped under a "Resume" heading, with a one-line description of what each session was about (infer from the first few lines of the file or from the matched context).

## Arguments

The user's search query is passed as the skill argument. For example:
- `/history? dependabot` — search for dependabot-related discussions
- `/history? billing UI revert` — search for when billing UI was reverted
- `/history? "libs.versions.toml"` — search for dependency version discussions

## Tips

- JSONL files can be very large. Use grep to find matching files first, then read only relevant sections.
- Recent conversations are in newer files (sort by mtime).
- Each JSONL line is a complete JSON message — parse it to extract the actual text content if needed.
- If too many results, prioritize the most recent session files.
