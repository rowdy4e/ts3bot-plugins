import json, os, subprocess


def tool(name, args):
    """Call a bot tool (listed in ts3bot.yml 'tools'); returns its answer, "ok: ..." or "error: ..."."""
    r = subprocess.run(["ts-tool", name, json.dumps(args)], capture_output=True, text=True)
    return r.stdout


city = os.environ.get("SVC_CITY", "Praha")                 # a setting
state_file = "/data/state.json"                            # the only writable place that lasts
state = json.load(open(state_file)) if os.path.exists(state_file) else {}

tool("say_channel", {"text": f"Hello from my-plugin ({city})"})

json.dump(state, open(state_file, "w"))
# Whatever it prints goes to people (the admins on a cron run): print nothing when there's nothing to say.
