#!/usr/bin/env bash
# Generate a PRODUCTION ed25519 signing keypair for the registry.
#
# Run this LOCALLY, once. The private seed is the registry's trust root — it
# authorizes plugin installs on every appliance. NEVER commit or paste it; put
# it only in the REGISTRY_SIGNING_KEY GitHub Actions secret.
set -euo pipefail
python3 - <<'PY'
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PrivateFormat, PublicFormat, NoEncryption,
)

k = Ed25519PrivateKey.generate()
seed = k.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
pub = k.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)

print("=== PRIVATE seed (base64) — GitHub secret REGISTRY_SIGNING_KEY, DO NOT COMMIT ===")
print(base64.b64encode(seed).decode())
print()
print("=== PUBLIC key (base64) — public/pubkey.txt AND appliance [registry].public_key ===")
print(base64.b64encode(pub).decode())
PY
