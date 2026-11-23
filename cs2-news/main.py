# New Counter-Strike 2 articles from Steam's news feed, posted into the bot's channel. The first run posts only the
# newest one (so the channel isn't flooded) and remembers the rest in /data.

import json, os, subprocess, urllib.request
import xml.etree.ElementTree as ET

FEED = "https://store.steampowered.com/feeds/news/app/730/"   # RSS se zprávami o CS2
SEEN = "/data/seen.json"                                      # /data přežije další běhy i restart


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def say(text):                                                # napsat do kanálu přes bota
    r = subprocess.run(["ts-tool", "say_channel", json.dumps({"text": text})], capture_output=True, text=True)
    if not r.stdout.startswith("ok"):
        raise SystemExit("say_channel failed: " + r.stdout)


items = [(i.findtext("link"), i.findtext("title")) for i in ET.fromstring(fetch(FEED)).iter("item")]
seen = json.load(open(SEEN)) if os.path.exists(SEEN) else None
new = items[:1] if seen is None else [x for x in items if x[0] not in seen]   # 1. běh: jen nejnovější
for link, title in reversed(new):
    say(f"[b]CS2:[/b] [url={link}]{title}[/url]")
json.dump(list(dict.fromkeys([x[0] for x in items] + (seen or [])))[:500], open(SEEN, "w"))
