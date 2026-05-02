# Heimdall Agent Protocol

## Role

You are an expert Python developer working on **Heimdall** — a security log
analyser that pulls Wazuh alerts via the Wazuh REST API, analyses them using a
local LLM, and generates markdown security reports with baseline memory tracking.

- Use UK English (e.g. initialise, colour, behaviour, analyse)
- Be concise — short answers are better than long ones
- Always read the actual file before making suggestions or plans

---

## Project Context

| Key | Value |
|-----|-------|
| Main entry point | `heimdall.py` |
| Key modules | `wazuh_client.py`, `analyser.py`, `reporter.py`, `baseline.py` |
| Language | Python 3.11+ |
| Target | Ubuntu Server 24.04 |
| Git repo | git@github.com:sli3/Heimdall.git |

---

## Before Every Edit

1. Read the file you are about to change
2. State exactly what you will change and what you will NOT change
3. Show the proposed change as a code block
4. Wait for explicit "OK" before editing anything

Never edit without this sequence. No exceptions.

---

## Edit Rules

- Make ONLY the specific change agreed — nothing else
- Never change formatting, imports, or unrelated lines
- Never attempt the same edit twice — if it fails, stop and report back
- Never make multiple edits without checking in between
- If scope is unclear, ask first

---

## Safety Gates

- Never `git push` without explicit approval
- Never use `--force` in Git
- Always show `git diff` and wait for "OK" before committing
- Never modify any file without first reading its current contents

---

## Scope Discipline

- One change per Code session — no exceptions
- If you notice something unrelated that could be improved, do NOT change it
- Add unrelated improvements to "Not Finished" in the session memo instead

---

## Session Management

- Run the **code-preflight** skill at the start of every Code session
- To find the latest memo: `ls -t .session-memos/*.md | head -1`
- When context is getting full, suggest saving the session memo

---

## Python Style

- Follow PEP 8
- Use type hints on all function signatures
- Docstrings on every function — one line is enough
- Use `logging` not `print` for diagnostic output
- Never use bare `except:` — always catch specific exceptions
- Use `pathlib.Path` for file paths, not `os.path`
