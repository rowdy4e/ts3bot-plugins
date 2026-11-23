# Two sources: TeamSpeak's own badge list - the file the client itself downloads, so a new badge shows up there
# first - and the community forum thread that posts every badge with its redeem code ("Badge Code: X (Available
# until: Y)"), usually the same day. The first run only remembers what's there and says so. With notify set, each
# of those people gets a private message - whoever is offline the moment it's found, the next time they're online
# (every run checks; nothing is lost while they're away).

import html, json, os, re, subprocess, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

LIST = "https://badges-content.teamspeak.com/list"
THREAD = "https://community.teamspeak.com/t/updated-teamspeak-badge-list/25184.rss"
STATE = "/data/state.json"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"}
REDEEM = "uplatníš v TeamSpeaku (Nastavení → Účet → Badges) nebo na [url=https://www.myteamspeak.com]myteamspeak.com[/url]"
NO_CODE = {"auto assign", "one-time code", "tba", "unknown", "none", "n/a", "-", ""}
GUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
# notify comes as "Name:UID,..." (the bot resolves the names): the UID decides, the name is only for the log.
NOTIFY = {e.rsplit(":", 1)[-1].strip(): e.rsplit(":", 1)[0].strip() for e in os.environ.get("SVC_NOTIFY", "").split(",") if e.strip()}


def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read()


# The list is protobuf: field 3 = a badge, and in it 1 guid, 2 name, 3 image URL (+ ".svg" / "_details.svg"),
# 4 description, 5 when it was added (seconds, or milliseconds in newer entries).
def varint(b, i):
    r = s = 0
    while True:
        x = b[i]
        i += 1
        r |= (x & 0x7F) << s
        s += 7
        if x < 0x80:
            return r, i


def fields(b):
    i = 0
    while i < len(b):
        key, i = varint(b, i)
        f, t = key >> 3, key & 7
        if t == 0:
            v, i = varint(b, i)
        elif t == 2:
            n, i = varint(b, i)
            v, i = b[i:i + n], i + n
        elif t == 1:
            v, i = b[i:i + 8], i + 8
        elif t == 5:
            v, i = b[i:i + 4], i + 4
        else:
            raise ValueError(f"wire type {t}")
        yield f, t, v


def badges():
    out = {}
    for f, t, v in fields(fetch(LIST)):
        if f != 3 or t != 2:
            continue
        b = {g: (w.decode("utf-8", "replace") if u == 2 else w) for g, u, w in fields(v)}
        if 1 in b and 2 in b:
            added = b.get(5, 0)
            out[b[1]] = {"name": b[2], "description": b.get(4, ""), "image": b.get(3, ""),
                         "added": added / 1000 if added > 10**11 else added}
    if not out:
        raise SystemExit("TeamSpeak's badge list came back empty - its format may have changed")
    return out


def codes():
    """{guid: (code, until)} from the forum thread's newest posts; {} when the forum is down (next time, then)."""
    try:
        root = ET.fromstring(fetch(THREAD))
    except Exception:
        return {}
    out = {}
    for item in root.iter("item"):
        text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(item.findtext("description") or "")))
        for part in text.split("Name:")[1:]:          # a post may add several badges
            g = GUID.search(part)
            m = re.search(r"Code:\s*(.+?)\s*\(Available until:\s*([^)]*)\)", part)
            if g and m:
                out.setdefault(g.group(0), (m.group(1).strip(), m.group(2).strip()))
    return out


def public(code):
    return code.strip().lower() not in NO_CODE


def tool(name, args):
    r = subprocess.run(["ts-tool", name, json.dumps(args)], capture_output=True, text=True)
    return r.stdout + r.stderr


def tell(text):
    """Into the channel - or, with notify set, into each of those people's outbox (deliver() sends it)."""
    if not NOTIFY:
        out = tool("say_channel", {"text": text})
        if not out.startswith("ok"):
            raise SystemExit("say_channel failed: " + out)
        return
    for uid in NOTIFY:
        box = state.setdefault("outbox", {}).setdefault(uid, [])
        box.append(text)
        del box[:-30]                                  # someone away for months gets the latest 30


def deliver():
    """Private messages to whoever of notify is online now - found by UID, not by name; the rest wait."""
    box = {u: t for u, t in (state.get("outbox") or {}).items() if u in NOTIFY and t}
    state["outbox"] = box
    if not box:
        return
    online = set(re.findall(r"^name=.*? uid=(\S+) ", tool("list_online", {}), re.M))
    for uid, texts in box.items():
        if uid not in online:
            continue
        while texts:
            if not tool("message_user", {"name": uid, "text": texts[0]}).startswith("ok"):
                break
            texts.pop(0)
            save(state)


def expired(until):
    try:
        return datetime.strptime(until.strip(), "%d.%m.%Y").date() < datetime.now().date()
    except ValueError:
        return False                                   # "unlimited", "TBA", another format: not known to be over


def code_line(code, until):
    if public(code) and expired(until):
        return f"Kód [b]{code}[/b] už vypršel (platil do {until})."
    if public(code):
        return f"Kód: [b]{code}[/b]" + (f" (platí do {until})" if until and until.lower() != "unlimited" else "") + f" · {REDEEM}"
    if code.strip().lower() == "auto assign":
        return "Nemá kód - přidělí se automaticky."
    return "Veřejný kód nemá."


def save(state):
    with open(STATE, "w") as f:
        json.dump(state, f)


bl = badges()
cd = codes()
state = json.load(open(STATE)) if os.path.exists(STATE) else None

if state is None:   # first run: remember everything, post nothing, say what it watches
    save({"badges": list(bl), "codes": {g: c for g, (c, _) in cd.items()}})
    newest = max(bl.values(), key=lambda b: b["added"])
    when = datetime.fromtimestamp(newest["added"], timezone.utc).strftime("%d.%m.%Y")
    print(f"Hlídám {len(bl)} TeamSpeak badges (a kódy z fóra: {len(cd)}). Nejnovější: {newest['name']} ({when}). "
          + (f"Každou novou napíšu soukromě: {', '.join(NOTIFY.values())} (kdo nebude online, dostane ji, až přijde)."
             if NOTIFY else "Každou novou napíšu do kanálu."))
    raise SystemExit(0)

seen = set(state["badges"])
new = sorted((g for g in bl if g not in seen), key=lambda g: bl[g]["added"])
for g in new:
    b = bl[g]
    text = f"🎖 Nová TeamSpeak badge: [b]{b['name']}[/b]" + (f" – {b['description']}" if b["description"] else "")
    text += "\n" + (code_line(*cd[g]) if g in cd else "Kód zatím není známý - napíšu ho, až se objeví.")
    if b["image"]:
        text += f" · [url={b['image']}_details.svg]obrázek[/url]"
    tell(text)
    state["badges"].append(g)
    if g in cd:
        state["codes"][g] = cd[g][0]
    save(state)

# A code that turned up after its badge was announced.
for g, (code, until) in cd.items():
    if g in seen and g not in state["codes"]:
        if public(code) and not expired(until):
            tell(f"🎖 TeamSpeak badge [b]{bl.get(g, {}).get('name', g)}[/b] – {code_line(code, until)}")
        state["codes"][g] = code
        save(state)

deliver()
save(state)
