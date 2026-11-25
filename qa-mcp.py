import os
import json
import subprocess
from pathlib import Path
import yaml

entry = yaml.safe_load(Path("catalogs/ace-music/catalog.yaml").read_text())["registry"]["ace-music"]
args = ["docker", "run", "--rm", "-i", "--network", "none", "-e", "ACEDATACLOUD_API_TOKEN", entry["image"], *entry["command"]]
env = dict(os.environ, ACEDATACLOUD_API_TOKEN="docker-catalog-fixture")
p = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, env=env)
def send(req):
    p.stdin.write(json.dumps({"jsonrpc":"2.0", **req}) + "\n")
    p.stdin.flush()
def receive(ident):
    for line in p.stdout:
        msg = json.loads(line)
        if msg.get("id") == ident:
            return msg["result"]
    raise RuntimeError("Missing MCP response")
try:
    send({"id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"docker-catalog-check","version":"1"}}})
    print("Handshake:", receive(1)["serverInfo"]["name"], flush=True)
    send({"method":"notifications/initialized"})
    send({"id":2,"method":"tools/list","params":{}})
    names=sorted(t["name"] for t in receive(2)["tools"])
    assert len(names)==11 and "acemusic_list_models" in names and "acemusic_get_task" in names
    print("Discovered:", ", ".join(names), flush=True)
    send({"id":3,"method":"tools/call","params":{"name":"acemusic_list_models","arguments":{}}})
    reply=receive(3)
    assert not reply.get("isError") and "acemusic-v1.1" in reply["content"][0]["text"] and "acemusic-v1" in reply["content"][0]["text"]
    print("Read-only model list:", reply["content"][0]["text"], flush=True)
finally:
    p.stdin.close()
    p.wait(timeout=20)
