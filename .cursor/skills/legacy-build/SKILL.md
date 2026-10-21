---
name: legacy-build
description: Build one modernization ticket in the target language while keeping every business rule. Use with a Jira story key.
disable-model-invocation: true
---
1. Read the Jira story you were given and its business rules, and its parent epic for the source program and target.
2. Build that piece in python/, following the project rules.
3. Keep every business rule, and cite its source line in a comment.
4. Never edit the original legacy code.
5. Commit on a new branch named after the ticket, push it, and open a pull request.
