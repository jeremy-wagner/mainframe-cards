---
name: legacy-build
description: Build one modernization ticket in the target language while keeping every business rule. Use with a Jira story key.
disable-model-invocation: true
---
1. Move the Jira story you were given to In Progress. Read it, its business rules, and its parent epic for the source program and target.
2. Build that piece in python/, following the project rules.
3. Keep every business rule, and cite its source line in a comment.
4. Never edit the original legacy code.
5. Commit on a new branch named after the ticket, push it, and open a pull request. Write the description for a reviewer who hasn't seen this work, with these sections:
   - Ticket: the Jira key and title, with a link.
   - Why: the business reason, from the epic.
   - What changed: the files added or changed, in plain language.
   - Business rules kept: a table of each rule, its COBOL source line, and where it lives in the Python.
   - Differences from the COBOL: anything that behaves differently, and why. Say "None" if there are none.
   - Security: how the secure coding rules were applied.
   - How it was checked: what you ran or compared to confirm the results match.
   - Where to focus the review: the one or two places most likely to be wrong.
6. Move the story to In Review and add the pull request link to it.
