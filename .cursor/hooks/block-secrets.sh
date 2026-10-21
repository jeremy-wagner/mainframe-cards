#!/bin/bash
input=$(cat)
echo "$(date) secrets-read: $input" >> /tmp/cursor-hooks.log
if echo "$input" | grep -Eq '"file_path": *"[^"]*(\.env|\.pem|\.key|secrets)[^"]*"'; then
  echo '{"permission":"deny","user_message":"Blocked: the agent cannot read secrets files."}'
else
  echo '{"permission":"allow"}'
fi
exit 0