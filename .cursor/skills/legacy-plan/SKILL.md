---
name: legacy-plan
description: Break a modernization epic into pieces that can ship one at a time, then create one Jira story per piece once the plan is approved. Use with an epic key.
disable-model-invocation: true
---
1. Read the epic you were given, including its business rules and constraints.
2. Break the work into pieces that can move one at a time. Each piece must be small enough for one pull request.
3. For each piece, list what it does, the business rules it must keep with source line numbers, and its dependencies.
4. Put the pieces in dependency order.
5. Stop and wait for the engineer to approve or change the plan.
6. Once approved, create one Jira story per piece under the epic, with its business rules as acceptance criteria. Then move each story to Ready.
