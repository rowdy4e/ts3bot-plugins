#!/bin/sh
# Without ts-tool (it's only in the bot's own images), any program talks to the bot the same way: an HTTP POST to
# /tool/<name> over the unix socket the bot mounts at $TS_BOT_SOCK, with $TS_BOT_TOKEN. Settings come as SVC_<KEY>.
text="Ahoj z vlastního Docker image ($(uname -m), $(date '+%H:%M'))${SVC_GREETING:+ - $SVC_GREETING}"
curl -s --unix-socket "$TS_BOT_SOCK" -X POST "http://localhost/tool/say_channel" \
     -H "X-Bot-Token: $TS_BOT_TOKEN" -H "Content-Type: application/json" \
     -d "$(jq -n --arg t "$text" '{text: $t}')"
echo
