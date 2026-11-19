#!/usr/bin/env python3
"""Add or replace one interpreter in the registry index.

    python scripts/update-interpreters.py <index.json> <kind> <version> <abi> <os> <arch> <url> <sha256> [size] [upstream] [eol] [--keep 3]

Interpreters live in a top-level `interpreters` list beside `plugins`, signed
with it. A plugin runtime fetches the one a placed plugin was built for, by
`kind` and `abi` (`python`, `cp313`), so a plugin package names its Python and
the runtime image doesn't have to. See homeCore's
docs/pythonInterpretersPlan.md.

Idempotent: replaces the entry for the same (kind, version, os, arch). Keeps the
newest `--keep` patches of each (kind, abi, os, arch), so the one before stays
available to roll back to. `eol` applies to the whole minor: a newer entry
marking it carries over to the older ones still listed.

Writes stable, sorted JSON as update-index.py does; signing is separate.
"""
import argparse
import functools
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from versions import compare_versions  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("kind")
    ap.add_argument("version")
    ap.add_argument("abi")
    ap.add_argument("os")
    ap.add_argument("arch")
    ap.add_argument("url")
    ap.add_argument("sha256")
    ap.add_argument("size", nargs="?", default="0")
    ap.add_argument("upstream", nargs="?", default="")
    ap.add_argument("eol", nargs="?", default="false")
    ap.add_argument("--keep", type=int, default=3)
    a = ap.parse_args()

    if not re.fullmatch(r"[a-z][a-z0-9-]*", a.kind):
        sys.exit(f"kind `{a.kind}` must be lowercase letters, digits and dashes")
    if a.kind == "python":
        m = re.fullmatch(r"3\.(\d+)\.\d+", a.version)
        if not m:
            sys.exit(f"a python interpreter's version is a final release like 3.13.18, not {a.version}")
        if a.abi != f"cp3{m.group(1)}":
            sys.exit(f"Python {a.version} is abi cp3{m.group(1)}, not {a.abi}")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", a.sha256):
        sys.exit("sha256 must be 64 hex digits")
    if a.keep < 1:
        sys.exit("--keep must be at least 1")
    eol = a.eol.strip().lower() in ("true", "1", "yes")

    idx = json.load(open(a.path)) if os.path.exists(a.path) else {"schema": "1", "plugins": []}
    entries = idx.setdefault("interpreters", [])

    entry = {
        "kind": a.kind,
        "version": a.version,
        "abi": a.abi,
        "os": a.os,
        "arch": a.arch,
        "url": a.url,
        "sha256": a.sha256.lower(),
        "size": int(a.size or 0),
        "key_id": "prod-1",
    }
    if a.upstream:
        entry["upstream"] = a.upstream
    if eol:
        entry["eol"] = True

    def slot(e):
        return (e["kind"], e["abi"], e["os"], e["arch"])

    entries[:] = [
        e for e in entries
        if not (slot(e) == slot(entry) and e["version"] == entry["version"])
    ]
    entries.append(entry)

    same = [e for e in entries if slot(e) == slot(entry)]
    if eol:
        for e in same:
            e["eol"] = True
    newest_first = sorted(
        same, key=functools.cmp_to_key(lambda x, y: compare_versions(y["version"], x["version"]))
    )
    dropped = newest_first[a.keep:]
    for e in dropped:
        entries.remove(e)
        print(f"dropped {e['kind']} {e['version']} ({e['os']}/{e['arch']}): {a.keep} newer are listed")

    entries.sort(
        key=functools.cmp_to_key(
            lambda x, y: (slot(x) > slot(y)) - (slot(x) < slot(y))
            or compare_versions(x["version"], y["version"])
        )
    )

    with open(a.path, "w") as f:
        json.dump(idx, f, indent=2)
        f.write("\n")
    print(f"indexed {a.kind} {a.version} ({a.abi}, {a.os}/{a.arch}) -> {a.url}")


if __name__ == "__main__":
    main()
