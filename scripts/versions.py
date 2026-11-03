"""Version ordering shared by the registry's index scripts."""
import re


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
