---
name: code-sanity-check
description: Logic and syntax verification for Python code. Run when user says "sanity check", "check this", or "verify this file". Always run before committing any new or heavily modified file.
---

## Sanity Check Protocol

### Steps

1. **Syntax**
   Run `ruff check` on the file.
   Fall back to `python -m py_compile` if ruff is unavailable.
   ```bash
   ruff check [file.py] || python -m py_compile [file.py]
   ```

2. **Logic**
   Check for:
   - Bare `except:` clauses (must catch specific exceptions)
   - Missing type hints on function signatures
   - `print()` used instead of `logging`
   - Hardcoded credentials, IPs, or paths that should come from config
   - `os.path` used instead of `pathlib.Path`

3. **Error Handling**
   Verify that:
   - API calls (Wazuh, LLM) have try/except around them
   - HTTP errors are checked (status codes, timeouts)
   - File I/O operations handle missing files gracefully

4. **Idempotency**
   Verify the module can be imported and run multiple times without side effects.
   Look for operations that would fail or corrupt state on a second run.

5. **Report**
   Summarise as one of:
   - ✅ **Passed** — no issues found
   - ⚠️ **Warnings** — issues found but not blocking; list each
   - ❌ **Failures** — blocking issues; list each and suggest fix

---

### Report Format

```
Sanity Check Report — [filename]
──────────────────────────────────
Syntax:         [Passed / Failed — reason]
Logic:          [Passed / Warnings — list]
Error Handling: [Passed / Concerns — list]
Idempotency:    [Passed / Concern — description]

Result: ✅ Passed / ⚠️ Warnings / ❌ Failures
[Summary of any action required]
```

---

### Rules

- Never modify the file during a sanity check — report only
- If failures are found, do not proceed with commit until resolved
- Always run this before `git-workflow` on a Code session
