---
name: code-preflight
description: Pre-flight checklist for Code sessions. Run at the start of every Code session before touching any file. Triggers on "run preflight", "preflight check", or at the start of any Code session.
---

## Code Pre-Flight Checklist

### Steps

1. **Read session memo:**
   ```bash
   ls -t .session-memos/*.md | head -1
   ```
   Summarise in one sentence what this Code session is supposed to do.

2. **Check previous mistakes** — look for `## Mistakes Made` in memo:
   - Read each mistake aloud
   - State how you will avoid repeating each one
   - If none, state that clearly

3. **State exact scope:**
   - Which file will be changed
   - Which function or section will be changed
   - What specific change will be made
   - What will NOT be changed

4. **Read only what is needed** — relevant function only, not entire file.

5. **Show the plan** — exact proposed change in a code block with inline comments.
   Do not edit yet.

6. **Wait for OK** — ask:
   > "Does this plan look correct? Shall I proceed?"

   Do not touch any file until user says yes.

---

### Checklist Output Format

```
Pre-Flight Check:
✅ Memo read — [one line summary]
✅ Previous mistakes reviewed — [none / list]
✅ Scope confirmed — changing [function] in [file] only
✅ Plan shown — waiting for your OK
```

---

### Rules

- Never skip this checklist in a Code session
- Never edit before user says OK
- If scope is unclear, ask — do not guess
- Always acknowledge previous mistakes before proceeding
