---
name: probe-anchor
description: "Use when the user asks to run the anchor probe, or says 'run anchor probe' / 'anchor probe'. Reports two verification tokens."
user_invocable: true
version: "1.0.0"
---

# Anchor Probe

A diagnostic skill. Follow these steps exactly.

1. Read the file `references/token.md` located in this skill's own directory.
2. Print exactly two lines and nothing else:

```
BODY=BODY-4B21E8
FILE=<the token string found in references/token.md>
```

If you cannot locate or read `references/token.md`, print `FILE=UNREACHABLE`
instead of guessing. Do not use any other tools. Do not explain.
