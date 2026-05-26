---
name: Playbook broken
about: A program's extraction stopped working (API changed, page redesign, etc.)
title: '[BROKEN] <program-name>: <short description>'
labels: 'broken-playbook'
---

**Program**: (e.g. World of Hyatt, IHG One Rewards)

**What you expected**:
<!-- e.g. "skill extracts ~50 stays into CSV, sum matches account balance" -->

**What actually happened**:
<!-- e.g. "fetch_activity.js returns {error: 'HTTP 401 — likely not logged in'} even though I'm logged in" -->

**Console output** (sanitized — remove account numbers, point balances if private):
```
<paste relevant errors / unexpected output>
```

**Did the program recently change**? (yes/no/unknown)
<!-- e.g. "Hyatt redesigned the activity page last week" — if known -->

**Suspected cause**, if you found it:
<!-- e.g. "endpoint changed from /stay/pastactivity to /stay/v2/activity"; "auth header rotated to new name" -->

**Browser**: (Chrome version)
**Plugin version**: (from `plugin.json`)
