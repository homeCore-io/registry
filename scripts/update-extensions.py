#!/usr/bin/env python3
"""Add or replace one UI extension release in the extensions index.

    python scripts/update-extensions.py <extensions.json> <id> <name> <version> <url> <sha256> [size] [values] [description] [category] [min_app] [preview_url] [preview_sha256]

The web app's UI extensions have an index of their own, signed with the same
key as the plugins' (sign-index.py), so homeCore never reads it: the app
fetches it, checks the signature, and installs extensions itself.

An extension is the same file on every machine, so a version has one artifact
and no os or arch. `values` is the version of the values the app gives its
drawings that this release expects; an app that only knows an older one leaves
it out. `min_app` is the oldest hc-web that can install it. `preview_url` and
`preview_sha256` are a picture or short video of how it looks, which the app
shows before installing, and only if it matches the checksum. `description` and
`category` are extension-level: blank keeps the indexed one.

Writes stable, sorted JSON, so re-running it over the same release changes
nothing and needs no new signature.
"""
import functools
import json
import os
import sys

from versions import compare_versions  # noqa: E402  (scripts/ is on the path)

(path, xid, name, version, url, sha256) = sys.argv[1:7]
arg = lambda i: sys.argv[i] if len(sys.argv) > i else ""  # noqa: E731
size = int(arg(7) or 0)
values = int(arg(8) or 1)
description = arg(9)
category = arg(10)
min_app = arg(11)
preview_url = arg(12)
preview_sha256 = arg(13).lower()
if bool(preview_url) != bool(preview_sha256):
    sys.exit("a preview needs both its url and its sha256")

idx = json.load(open(path)) if os.path.exists(path) else {"schema": "1", "extensions": []}
idx.setdefault("schema", "1")
idx.setdefault("extensions", [])

ext = next((x for x in idx["extensions"] if x["id"] == xid), None)
if ext is None:
    ext = {"id": xid, "name": name, "description": "", "category": "", "versions": []}
    idx["extensions"].append(ext)
ext["name"] = name
if description:
    ext["description"] = description
if category:
    ext["category"] = category

rel = {"version": version, "values": values, "url": url, "sha256": sha256, "key_id": "prod-1"}
if size:
    rel["size"] = size
if min_app:
    rel["min_app"] = min_app
if preview_url:
    rel["preview"] = {"url": preview_url, "sha256": preview_sha256}
ext["versions"] = [v for v in ext["versions"] if v["version"] != version] + [rel]

idx["extensions"].sort(key=lambda x: x["id"])
for x in idx["extensions"]:
    x["versions"].sort(key=functools.cmp_to_key(lambda a, b: compare_versions(a["version"], b["version"])))

with open(path, "w") as f:
    json.dump(idx, f, indent=2)
    f.write("\n")
print(f"indexed extension {xid} {version} -> {url}")
