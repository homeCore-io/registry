#!/usr/bin/env python3
"""Add or replace one artifact entry in the registry index.

    python scripts/update-index.py <index.json> <id> <name> <version> <os> <arch> <url> <sha256> [size] [min_core]

Idempotent: replaces the artifact for the same (id, version, os, arch), creating
the plugin/version entries as needed. Writes stable, sorted JSON so re-runs are
deterministic. Signing happens separately (sign-index.py) over the exact bytes
this writes.
"""
import json
import os
import sys

(path, pid, name, version, os_, arch, url, sha256) = sys.argv[1:9]
size = int(sys.argv[9]) if len(sys.argv) > 9 and sys.argv[9] else 0
min_core = sys.argv[10] if len(sys.argv) > 10 else ""

idx = json.load(open(path)) if os.path.exists(path) else {"schema": "1", "plugins": []}
idx.setdefault("schema", "1")
idx.setdefault("plugins", [])

plug = next((p for p in idx["plugins"] if p["id"] == pid), None)
if plug is None:
    plug = {"id": pid, "name": name, "description": "", "category": "", "versions": []}
    idx["plugins"].append(plug)
plug["name"] = name
plug.setdefault("versions", [])

ver = next((v for v in plug["versions"] if v["version"] == version), None)
if ver is None:
    ver = {"version": version, "artifacts": []}
    plug["versions"].append(ver)
if min_core:
    ver["min_core"] = min_core

art = {"os": os_, "arch": arch, "url": url, "sha256": sha256, "key_id": "prod-1"}
if size:
    art["size"] = size
ver["artifacts"] = [a for a in ver["artifacts"] if not (a["os"] == os_ and a["arch"] == arch)]
ver["artifacts"].append(art)

# Deterministic ordering so the signed bytes only change when content changes.
idx["plugins"].sort(key=lambda p: p["id"])
for p in idx["plugins"]:
    p["versions"].sort(key=lambda v: v["version"])
    for v in p["versions"]:
        v["artifacts"].sort(key=lambda a: (a["os"], a["arch"]))

with open(path, "w") as f:
    json.dump(idx, f, indent=2)
    f.write("\n")
print(f"indexed {pid} {version} ({os_}/{arch}) -> {url}")
