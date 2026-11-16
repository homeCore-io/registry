"""Keep the newest few versions of each plugin in the registry index.

    python scripts/prune-index.py public/index.json [--keep 3] [--dry-run]

An index entry is what core installs from, so a version taken out here can no
longer be installed or rolled back to. Three leaves the newest and two to
step back to. The GitHub releases those entries point at are pruned
separately (hc-scripts/prune-releases.sh).

Writes stable, sorted JSON as update-index.py does, so pruning nothing makes no
diff and no new signature. Prints what it keeps and drops, per plugin.
Works on extensions.json too, which has the same shape.
"""
import argparse
import functools
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from versions import compare_versions  # noqa: E402


def prune(index, keep):
    """Drop all but the newest `keep` versions of each entry. Returns the
    dropped versions, by id."""
    dropped = {}
    newest_first = functools.cmp_to_key(lambda a, b: compare_versions(b["version"], a["version"]))
    for entry in index.get("plugins", index.get("extensions", [])):
        versions = sorted(entry.get("versions", []), key=newest_first)
        if len(versions) > keep:
            dropped[entry["id"]] = [v["version"] for v in versions[keep:]]
            # Back in the order update-index.py keeps them: oldest first.
            entry["versions"] = sorted(
                versions[:keep], key=functools.cmp_to_key(lambda a, b: compare_versions(a["version"], b["version"]))
            )
    return dropped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--keep", type=int, default=3)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.keep < 1:
        sys.exit("--keep must be at least 1: an entry with no versions cannot be installed at all")

    with open(args.path) as f:
        index = json.load(f)
    dropped = prune(index, args.keep)

    if not dropped:
        print(f"{args.path}: nothing to prune (every entry has {args.keep} versions or fewer)")
        return
    total = sum(len(v) for v in dropped.values())
    print(f"{args.path}: {'would drop' if args.dry_run else 'dropping'} {total} versions, keeping the newest {args.keep} of each")
    for pid, versions in sorted(dropped.items()):
        print(f"  {pid}: {', '.join(versions)}")
    if args.dry_run:
        return
    with open(args.path, "w") as f:
        json.dump(index, f, indent=2, sort_keys=False)
        f.write("\n")


if __name__ == "__main__":
    main()
