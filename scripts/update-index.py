#!/usr/bin/env python3
"""Add or replace one artifact entry in the registry index.

    python scripts/update-index.py <index.json> <id> <name> <version> <os> <arch> <url> <sha256> [size] [min_core] [description] [runtime] [abi] [category]

Idempotent: replaces the artifact for the same (id, version, os, arch, runtime,
abi), creating the plugin/version entries as needed. Writes stable, sorted JSON
so re-runs are deterministic. Signing happens separately (sign-index.py) over
the exact bytes this writes.

`description` is the plugin's one-line summary, shown on its card in the web
UI's registry browser. It is plugin-level rather than version-level: the newest
release to carry one wins.

`category` groups the plugin in the web app's Store (Lighting, Media, …);
like `description` it is plugin-level, and blank keeps the indexed one.

`runtime` and `abi` describe artifacts that are not native binaries. `runtime`
defaults to "native", which is what every entry published before plugin
runtimes existed means, so an older publisher keeps working untouched and core
reads those entries exactly as it always did. A `python` artifact carries an
`abi` such as `cp312-manylinux_2_28`, because two Python builds of the same
plugin for the same architecture are different artifacts — and identity has to
include the ABI or one would silently replace the other.
"""
import functools
import json
import os
import sys

(path, pid, name, version, os_, arch, url, sha256) = sys.argv[1:9]
size = int(sys.argv[9]) if len(sys.argv) > 9 and sys.argv[9] else 0
min_core = sys.argv[10] if len(sys.argv) > 10 else ""
description = sys.argv[11] if len(sys.argv) > 11 else ""
runtime = (sys.argv[12] if len(sys.argv) > 12 else "") or "native"
abi = sys.argv[13] if len(sys.argv) > 13 else ""
category = sys.argv[14] if len(sys.argv) > 14 else ""

if runtime != "native" and not abi:
    sys.exit(f"a {runtime} artifact must carry an abi — without one it cannot be matched to a runtime")
if runtime == "native" and abi:
    sys.exit("a native artifact has no abi: os and arch already say everything about it")

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
if category:
    plug["category"] = category
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
# Emitted only when they say something. A native entry stays byte-identical to
# what this script has always written, so re-running it over the live index
# produces no diff and no new signature.
if runtime != "native":
    art["runtime"] = runtime
    art["abi"] = abi


def same_artifact(a):
    """Identity of an artifact slot: what it runs on, and what runs it.

    An entry written before runtimes existed has no `runtime` key and means
    native, so absent and "native" have to compare equal — otherwise the first
    re-publish of an existing plugin would append a duplicate rather than
    replace it.
    """
    return (
        a["os"] == os_
        and a["arch"] == arch
        and a.get("runtime", "native") == runtime
        and a.get("abi", "") == abi
    )


ver["artifacts"] = [a for a in ver["artifacts"] if not same_artifact(a)]
ver["artifacts"].append(art)

from versions import compare_versions  # noqa: E402  (scripts/ is on the path)


# Deterministic ordering so the signed bytes only change when content changes.
idx["plugins"].sort(key=lambda p: p["id"])
for p in idx["plugins"]:
    p["versions"].sort(key=functools.cmp_to_key(lambda a, b: compare_versions(a["version"], b["version"])))
    for v in p["versions"]:
        # Sorted by the same tuple that identifies one, so a version publishing
        # a native binary and two Python builds writes them in a stable order
        # and re-signing produces no spurious diff.
        v["artifacts"].sort(
            key=lambda a: (a["os"], a["arch"], a.get("runtime", "native"), a.get("abi", ""))
        )

with open(path, "w") as f:
    json.dump(idx, f, indent=2)
    f.write("\n")
print(f"indexed {pid} {version} ({os_}/{arch}) -> {url}")
