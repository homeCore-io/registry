#!/usr/bin/env python3
"""Sign the registry index with the production ed25519 key.

    REGISTRY_SIGNING_KEY=<base64 seed> python scripts/sign-index.py [public/index.json]

Writes `<index>.sig` = base64 of the detached 64-byte ed25519 signature over the
EXACT bytes of the index file. Core verifies this same signature, so the file
must not be reformatted between signing and serving.
"""
import base64
import os
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

path = sys.argv[1] if len(sys.argv) > 1 else "public/index.json"

seed_b64 = os.environ.get("REGISTRY_SIGNING_KEY")
if not seed_b64:
    sys.exit("REGISTRY_SIGNING_KEY (base64 of the 32-byte seed) is not set")
seed = base64.b64decode(seed_b64)
if len(seed) != 32:
    sys.exit(f"signing key must be 32 bytes, got {len(seed)}")

key = Ed25519PrivateKey.from_private_bytes(seed)
data = open(path, "rb").read()
sig = key.sign(data)  # standard detached 64-byte ed25519 signature
open(path + ".sig", "w").write(base64.b64encode(sig).decode())
print(f"signed {path} ({len(data)} bytes) -> {path}.sig")
