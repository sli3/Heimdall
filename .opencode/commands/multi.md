---
description: >
  Run two or more agents in parallel on the same task and synthesise
  their results. Mention agents by @name in your message.
  Example: /multi @plan-reviewer @deep-bug-hunter assess the risk of
  switching baseline.py to async writes
subtask: false
---

You are coordinating a parallel agent run for the Heimdall project.

Spawn each @mentioned agent simultaneously as independent subagents, giving
each the same task described in this message. Do not start one and wait for
it to finish before starting the next — launch all of them at the same time.

Wait until all subagents have reported back, then synthesise their findings
into a single coherent response. Highlight where agents agreed, where they
disagreed, and which recommendation to act on.

Do not write or modify any files until synthesis is complete and Prin has
confirmed the direction.
