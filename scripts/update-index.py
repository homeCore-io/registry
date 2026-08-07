#!/usr/bin/env python3
"""Add or replace one artifact entry in the registry index.

    python scripts/update-index.py <index.json> <id> <name> <version> <os> <arch> <url> <sha256> [size] [min_core] [description]

Idempotent: replaces the artifact for the same (id, version, os, arch), creating
the plugin/version entries as needed. Writes stable, sorted JSON so re-runs are
deterministic. Signing happens separately (sign-index.py) over the exact bytes
this writes.

`description` is the plugin's one-line summary, shown on its card in the web
UI's registry browser. It is plugin-level rather than version-level: the newest
release to carry one wins.
"""
import functools
import json
import os
import re
import sys

(path, pid, name, version, os_, arch, url, sha256) = sys.argv[1:9]
size = int(sys.argv[9]) if len(sys.argv) > 9 and sys.argv[9] else 0
min_core = sys.argv[10] if len(sys.argv) > 10 else ""
description = sys.argv[11] if len(sys.argv) > 11 else ""

idx = json.load(open(path)) if os.path.exists(path) else {"schema": "1", "plugins": []}
idx.setdefault("schema", "1")
idx.setdefault("plugins", [])

plug = next((p for p in idx["plugins"] if p["id"] == pid), None)
if plug is None:
    plug = {"id": pid, "name": name, "description": "", "category": "", "versions": []}
    idx["plugins"].append(plug)
plug["name"] = name
# Only overwrite when this release actually carried one. An older publisher, or
# a manual run that omits it, must not blank out a description already indexed.
if description:
    plug["description"] = description
plug.setdefault("description", "")
plug.setdefault("category", "")
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

def compare_versions(a, b):
    """Order version strings by numeric segment, so 0.1.9 comes before 0.1.10.

    This sorted on the raw string until 2026-08-07, which put "0.1.14" ahead of
    "0.1.4" and left the newest release somewhere in the middle of the list.
    Core read the last entry as the latest, so a fresh install of nine of the
    eleven plugins pulled a version several releases old.

    Same rules as core's `compare_versions` and hc-web's `compareVersions`, and
    written the same way on purpose — all three decide part of "which version is
    newest", and a clever sort key that disagreed in one edge case would be a
    much harder bug to find than this loop is to read. Not full semver:

      - segments split on `.`, `+` and `-`; numeric pairs compare numerically
        and anything else compares as text, so a suffix is ordered not fatal,
      - a numeric extra segment means more version (0.2 < 0.2.1), while a
        non-numeric one is a pre-release of the release it leads to
        (0.2.0-rc1 < 0.2.0).
    """
    x = [p for p in re.split(r"[.+-]", a) if p]
    y = [p for p in re.split(r"[.+-]", b) if p]
    for i in range(max(len(x), len(y))):
        l = x[i] if i < len(x) else None
        r = y[i] if i < len(y) else None
        ln = int(l) if l is not None and l.isdigit() else None
        rn = int(r) if r is not None and r.isdigit() else None

        # One side ran out of segments: a numeric extra is more version, a
        # non-numeric extra is a pre-release of what the other side is.
        if l is None:
            return -1 if rn is not None else 1
        if r is None:
            return 1 if ln is not None else -1

        if ln is not None and rn is not None:
            c = (ln > rn) - (ln < rn)
        else:
            c = (l > r) - (l < r)
        if c:
            return c
    return 0


# Deterministic ordering so the signed bytes only change when content changes.
idx["plugins"].sort(key=lambda p: p["id"])
for p in idx["plugins"]:
    p["versions"].sort(key=functools.cmp_to_key(lambda a, b: compare_versions(a["version"], b["version"])))
    for v in p["versions"]:
        v["artifacts"].sort(key=lambda a: (a["os"], a["arch"]))

with open(path, "w") as f:
    json.dump(idx, f, indent=2)
    f.write("\n")
print(f"indexed {pid} {version} ({os_}/{arch}) -> {url}")
