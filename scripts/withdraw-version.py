"""Take one version of one plugin out of the registry index.

    python scripts/withdraw-version.py public/index.json <id> <version> [--dry-run]

For a release that should never have been installable: published under the
wrong number, or broken. Core can no longer install it or roll back to it; a
house that already runs it keeps running it. A plugin left with no versions is
taken out of the index altogether. The GitHub Release the entry pointed at is
not touched here.

Writes JSON as prune-index.py does, so the signature changes only when the
index does.
"""
import argparse
import json
import sys


def withdraw(index, plugin_id, version):
    """Remove the version. Returns what happened, in words, or None if there was nothing to remove."""
    plugins = index.get("plugins", [])
    for i, entry in enumerate(plugins):
        if entry.get("id") != plugin_id:
            continue
        kept = [v for v in entry.get("versions", []) if v.get("version") != version]
        if len(kept) == len(entry.get("versions", [])):
            return None
        if kept:
            entry["versions"] = kept
            return f"{plugin_id} {version} withdrawn; {', '.join(v['version'] for v in kept)} remain"
        del plugins[i]
        return f"{plugin_id} {version} withdrawn; it was the only version, so {plugin_id} is no longer listed"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("plugin_id")
    ap.add_argument("version")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    with open(args.path) as f:
        index = json.load(f)
    said = withdraw(index, args.plugin_id, args.version)
    if said is None:
        sys.exit(f"{args.path}: {args.plugin_id} {args.version} is not in the index")
    print(("would be: " if args.dry_run else "") + said)
    if args.dry_run:
        return
    with open(args.path, "w") as f:
        json.dump(index, f, indent=2, sort_keys=False)
        f.write("\n")


if __name__ == "__main__":
    main()
