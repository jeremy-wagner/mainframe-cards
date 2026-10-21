---
name: legacy-modernize
description: Understand a legacy program, plan its migration in small pieces, create Jira tickets, and build one piece.
---
1. Explain the application and list every business rule with its source line.
2. Plan the migration in pieces small enough for one pull request each, in dependency order.
3. Create one Jira story per piece under the epic, with its business rules as acceptance criteria.
4. Build one piece in python/ following the project rules. Never edit the COBOL.