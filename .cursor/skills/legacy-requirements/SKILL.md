---
name: legacy-requirements
description: Explain a legacy program for an engineer who has never read it, and document its business rules, dependencies and migration risks in the Jira epic. Use with a Jira epic key.
disable-model-invocation: true
---
1. Read the Jira epic you were given. It names the source program, the target and the constraints. Then explain what the program does for an engineer who has never read the language it's written in.
2. Map the programs, files and copybooks it depends on.
3. List every business rule with its source file and line number.
4. Flag anything that would behave differently in the target language, such as rounding, truncation or date handling.
5. Update the Jira epic you were given with three sections: "Business rules" (step 3), "Dependencies" (step 2) and "Migration risks" (step 4, most likely to break first). Replace any placeholder text in those sections.