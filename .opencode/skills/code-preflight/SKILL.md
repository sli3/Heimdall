---
name: code-preflight
description: Pre-flight checklist for Code sessions ONLY. Triggers on "run preflight", "preflight check", or when the user explicitly says "Code session". NEVER triggers for Plan, Explore, or Review sessions. Do not run this skill unless the session type is explicitly Code.
---

## Code Pre-Flight Checklist

### Steps

1. **Read session memo:**
```bash
   ls -t .session-memos/*.md | head -1
```
   Summarise in one sentence what this Code session is supposed to do.
   
1b. **If this is a roadmap feature session**, read the relevant feature section from `docs/HEIMDALL_ROADMAP.md` before stating scope.

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

7. **Remind user of post-edit sequence:**
   > "After the edit is done: run `@cloud-reviewer` on the changed function,
   > then `code-sanity-check`, then `git-workflow`."

---

### Checklist Output Format
Pre-Flight Check:
✅ Memo read — [one line summary]
✅ Previous mistakes reviewed — [none / list]
✅ Scope confirmed: [file1.py, file2.toml] (colon + explicit file list, no em dash)
✅ Plan shown — waiting for your OK
✅ Post-edit sequence noted — @cloud-reviewer → sanity-check → git-workflow

---

### Rules

- Never skip this checklist in a Code session
- Never edit before user says OK
- If scope is unclear, ask — do not guess
- Always acknowledge previous mistakes before proceeding
- Never invoke @cloud-reviewer yourself — remind the user to do it manually
- Never touch files outside the stated scope — if another file needs changing, STOP and report back to the user before proceeding
- Never create any file before the user says OK