# Review rules

## Security (blocking)
- Flag SQL or shell commands built from strings or f-strings.
- Flag hard-coded secrets, tokens or passwords.
- Flag logging of card numbers, account numbers or personal data.
- Flag external input that isn't validated.
- Flag new or unpinned dependencies.

## Migration correctness (blocking)
- Flag money stored or calculated as float. It must be decimal.Decimal.
- Flag any change to the original COBOL files.
- Flag business logic with no comment citing its COBOL source line.