---
name: bug-hunt-loop
description: Run a file, capture errors, apply a targeted fix, and re-run. Loops up to 3 iterations. Triggers on "bug hunt", "hunt bugs", "fix and run", or "run bug hunt on [filename]". Shows a diff and states every change before applying. Writes bug-hunt-report.md on failure. Uses whichever model is active — ensure you are on the local model before triggering to preserve OpenRouter quota.
---

## Bug Hunt Loop

### Purpose

Run a file, observe failures, apply a targeted fix, and re-run — up to three times.
Every change is shown as a diff before it is applied. Nothing is edited silently.
On three consecutive failures, the loop stops and writes `bug-hunt-report.md` to the project root.

---

### Model note

This skill cannot detect which model is currently active, and cannot switch models itself.
Model selection is a manual action — it happens outside the skill, in the OpenCode TUI.

**Before triggering this skill, ensure you are on your local model** (not OpenRouter).
This skill runs up to 3 iterations with multiple tool calls per iteration. On the OpenRouter free tier (200 req/day), a single bug hunt can consume a significant portion of your daily quota.

If you are unsure which model is active, check the model indicator in the TUI before proceeding.

---

### Pre-flight

Before doing anything, warn the user:
> "⚠️ This skill will edit the file directly. Make sure your recent changes are committed or stashed before I proceed. Shall I continue?"

Wait for explicit confirmation. Do not proceed without it.

---

### Step 1 — Detect language and runner

Check the file extension first. If the extension is absent or ambiguous, read the shebang line:

```bash
head -1 [filename]
```

Use this table to select the runner:

| Extension / Shebang | Runner |
|---|---|
| `.sh` or `#!/usr/bin/env bash` or `#!/bin/bash` | `bash` |
| `.py` or `#!/usr/bin/env python3` or `#!/usr/bin/env python` | `python3` |
| `.js` | `node` |
| `.ts` | `npx tsx` |
| `.go` | `go run` |
| `.rb` | `ruby` |
| Unrecognised | Stop — report unrecognised language and ask the user how to run it |

Before proceeding, state the detected language and runner:
> "Detected: [language] — will run with: [runner]"

**Runner availability check:**
```bash
command -v [runner] >/dev/null 2>&1 || echo "NOT FOUND"
```
If the runner is not installed, stop immediately and report — do not attempt to install it.

**Project structure check (Go only):**
For `.go` files, confirm `go.mod` exists in the project root before using `go run`.
If it does not exist, stop and report — do not attempt to create it.

---

### Step 2 — Initial run

Run the file and capture both stdout and stderr. Always capture the exit code.

```bash
output=$([runner] [filename] 2>&1)
exit_code=$?
printf 'Exit code: %s\n' "${exit_code}"
printf '%s\n' "${output}"
```

If exit code is 0 and output contains no error indicators:
> "✅ No errors detected on first run. Bug hunt complete — no changes made."

Stop here. Do not proceed to the loop.

---

### Step 3 — The fix loop (maximum 3 iterations)

Repeat the following sequence. Track the current iteration number explicitly at every step.
Never exceed 3 iterations under any circumstance.

---

#### 3a — Diagnose

Read the captured output carefully. State:
- The exact error message
- The file and approximate line number causing it
- The proposed fix in one sentence

---

#### 3b — Show diff

Before touching the file, display the proposed change as a diff block:

```
Iteration [n] — proposed fix:

--- before
+++ after
@@ ~line [n] @@
- [original line as it currently exists in the file]
+ [replacement line]
```

Then state: `"Applying fix now."`

Do not wait for approval. Transparency comes from showing the diff — not from gating the loop.

---

#### 3c — Apply the fix

Edit the file using the minimum change needed to address the diagnosed error.

- Fix only the diagnosed error — nothing else
- Do not reformat unrelated lines
- Do not fix other issues noticed in passing — note them in the report instead
- If iteration 2 would apply an identical change to iteration 1, stop immediately and proceed to Step 4

---

#### 3d — Re-run and capture

```bash
output=$([runner] [filename] 2>&1)
exit_code=$?
printf 'Exit code: %s\n' "${exit_code}"
printf '%s\n' "${output}"
```

---

#### 3e — Evaluate

| Result | Action |
|---|---|
| Exit code 0, no errors | Report success and stop |
| Still failing, iteration < 3 | State `"Iteration [n] failed — proceeding to iteration [n+1]"` and repeat from 3a |
| Still failing, iteration = 3 | Proceed to Step 4 |

---

### Step 4 — Write failure report

Write `bug-hunt-report.md` to the project root using this format:

```markdown
# Bug Hunt Report — [filename]

**Date:** [YYYY-MM-DD HH:MM]
**Language:** [detected language]
**Runner:** [runner used]
**Result:** ❌ Unresolved after 3 iterations

---

## Iteration 1

**Error output:**
[exact captured output]

**Fix applied:**
[one-line description of the change]

**Diff:**
[diff block shown before the edit]

**Output after fix:**
[captured output after re-run]

---

## Iteration 2

[same structure as Iteration 1]

---

## Iteration 3

[same structure as Iteration 1]

---

## Final output

[last captured stdout and stderr verbatim]

---

## Issues noticed but not fixed

[list any unrelated issues observed during the hunt — do not fix these]

## Suggested next steps

- [specific suggestion based on the last error message]
- Consider running the `code-sanity-check` skill on this file
- Review manually — the root cause may require structural changes beyond single-line fixes
```

After writing the report, state:
> "Bug hunt failed after 3 iterations. Report saved to `bug-hunt-report.md`. No further edits will be made."

Stop completely.

---

### Rules

- **Hard cap of 3 iterations** — never attempt a 4th fix under any circumstance
- **Never edit silently** — always show the diff block and state what is changing before applying
- **One error per iteration** — fix only the diagnosed error, nothing else
- **Never repeat the same fix** — if the proposed change is identical to a previous iteration, stop and write the report immediately
- **Always capture exit code** — do not rely on output text alone to judge success or failure
- **Cannot detect or switch the active model** — ensure you are on the local model before triggering this skill to preserve OpenRouter free tier quota
- **Pre-flight is mandatory** — never begin without the user's explicit confirmation
- If the target file does not exist, stop immediately and report — do not create it
- If the runner is not installed, stop and report — do not attempt to install it
- If the file passes on the first run, stop and report success — do not make any changes
