#!/bin/bash
input=$(cat)
echo "$(date) push: $input" >> /tmp/cursor-hooks.log
if echo "$input" | grep -q 'git push'; then
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  if [ "$branch" = "main" ] || [ "$branch" = "master" ] || echo "$input" | grep -Eq 'git push[^"]*(main|master)'; then
    echo '{"permission":"deny","user_message":"Blocked: changes to main need a pull request.","agent_message":"Pushing to main is blocked by policy. Open a pull request instead."}'
    exit 0
  fi
fi
echo '{"permission":"allow"}'
exit 0