#!/bin/bash
input=$(cat)
echo "$(date) secrets-shell: $input" >> /tmp/cursor-hooks.log
if echo "$input" | grep -Eq '"command": *"[^"]*(\.env|\.pem|\.key|secrets)'; then
  echo '{"permission":"deny","user_message":"Blocked: the agent cannot read secrets files.","agent_message":"Reading secrets files is blocked by policy."}'
else
  echo '{"permission":"allow"}'
fi
exit 0