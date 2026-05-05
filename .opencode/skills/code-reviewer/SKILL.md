---
name: code-reviewer
description: Read-only code review against project context and recent session changes. Triggers on "review", "code review", "review this function", "review [filename]", or "run code review". Reports bugs, logic errors, and environment mismatches. Never edits. Switch to the cloud model manually before triggering — this skill cannot detect or change the active model.
---

## Code Reviewer

### Purpose

Review a specific function or section of code against three sources of truth:
- The project's target environment and constraints (`AGENTS.md`)
- What was recently changed (latest session memo)
- The actual current state of the file

Reports only. **Never edits any file under any circumstance.**

---

### Model note

This skill cannot detect which model is currently active, and cannot switch models itself.
Model selection is a manual action — it happens outside the skill, in the OpenCode TUI.

For best results, **before triggering this skill**:
1. Press `Ctrl+K` in the TUI
2. Select `openrouter/qwen/qwen3-coder:free`
3. Then trigger the review

If you are on the local model and want to proceed anyway, the review will still run — quality may vary depending on the local model's capability.

---

### Steps

1. **Read project context**
   ```bash
   cat AGENTS.md
   ```
   Extract and note internally:
   - Target environment (OS, runtime, shell version)
   - Agent role and language stack
   - Any stated edit rules, constraints, or forbidden patterns

   Do **not** include this content in the review output verbatim.

2. **Read the latest session memo**
   ```bash
   ls -t .session-memos/*.md | head -1
   ```
   Read the file. Note internally:
   - What was changed in the last Code session
   - Files touched
   - Any mistakes recorded

   Do **not** include this content in the review output verbatim.

3. **Identify the review target**
   If not already stated, ask:
   > "Which file and function should I review? (e.g. `setup.sh :: rotate_logs`)"

   Read **only the named function or section** from the file — not the whole file.
   If the function boundary is ambiguous, include the minimal surrounding context needed and note this in the report.

4. **Sanitise the extract**
   Before using the extracted function in any review step, scan it for:
   - IPv4 addresses matching the pattern `\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}`
   - Strings that look like API keys, tokens, passwords, or secrets (e.g. long hex/base64 strings, patterns like `key=`, `token=`, `password=`, `secret=`)
   - Internal hostnames or non-public domain names

   For each match found:
   - Replace the value with `[REDACTED]` in the working extract
   - Warn the user before proceeding:
     > "⚠️ Sensitive-looking value redacted before review: [describe the type, not the value] on line ~[n]"

   If nothing is found, state: "No sensitive values detected in extract."

5. **Run the review**
   Using only the sanitised function extract and the context noted in Steps 1–2, evaluate for:

   - **Bugs** — logic errors, off-by-one, incorrect conditionals, missing return code checks
   - **Environment mismatches** — anything incompatible with the stated target (e.g. Bash-only syntax on a POSIX `sh` target, Python 3.x syntax on a Python 2 environment, Debian-specific commands on an Alpine target)
   - **Style violations** — anything inconsistent with `AGENTS.md` rules or the relevant style skill (e.g. `bash-style`: missing `set -euo pipefail`, unquoted variables, `#!/bin/bash` shebang)
   - **Regressions** — anything that contradicts or undoes the change recorded in the last session memo
   - **Security concerns** — hardcoded values remaining after redaction, unsafe permissions, unvalidated inputs, commands run as root without justification

6. **Report**
   Output findings using this exact format:

   ```
   Code Review Report — [filename] :: [function name]
   ────────────────────────────────────────────────────
   Reviewed against:  [target environment from AGENTS.md]
   Last change:       [one-line summary from session memo, or "No memo found"]
   Sensitive values:  [Redacted: n items / None detected]

   BUGS
     [BUG-01] [description] — Line ~[n] — Severity: High / Medium / Low
     None found.

   LOGIC ERRORS
     [LOG-01] [description] — Line ~[n]
     None found.

   ENVIRONMENT MISMATCHES
     [ENV-01] [description] — Line ~[n]
     None found.

   STYLE VIOLATIONS
     [STY-01] [description] — Line ~[n]
     None found.

   REGRESSIONS
     [REG-01] [description]
     None found.

   SECURITY
     [SEC-01] [description] — Line ~[n]
     None found.

   ────────────────────────────────────────────────────
   Overall: ✅ Clean / ⚠️ Warnings / ❌ Issues found

   Recommended actions:
     - [action if any]
     - None required.
   ```

---

### Rules

- **Never edit any file** — this skill reports only, always
- **Never include more than the specific function extract** in any review step — not the whole file
- **Always redact** IPs, credentials, tokens, and internal hostnames before review, and warn the user
- **Cannot detect or switch the active model** — model selection must be done manually before triggering this skill
- If no session memo exists, state this clearly and proceed using `AGENTS.md` context only
- If the user names a whole file with no function specified, ask which function to start with — do not review the entire file
- One function per invocation — complete the report before accepting another target
