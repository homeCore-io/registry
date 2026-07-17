# homeCore plugin registry

The signed index of installable plugins. Appliances fetch `index.json` +
`index.json.sig`, verify a detached **ed25519** signature over the exact bytes
of `index.json`, then download each artifact and check its `sha256`. Serving is
100% static (GitHub Pages) — there is no server.

- **Index + signature + pubkey** live here under `public/` and are served at
  `https://homeCore-io.github.io/registry/` (GitHub Pages, source = `public/`).
- **Artifacts** (`plugin.<id>-<ver>.tar.zst`) are NOT in this repo — they are
  hosted as **GitHub Release assets** on each plugin repo, and the index entries
  point at those download URLs.

## Trust root

`public/pubkey.txt` is the base64 ed25519 **public** key. The matching **private**
key is a GitHub Actions secret **`REGISTRY_SIGNING_KEY`** (base64 of the 32-byte
seed) and is never committed. The same public key is baked into every appliance's
`[registry].public_key`, so an appliance only installs plugins signed by this key.

## Publishing (P2: plugin releases call this)

A plugin release uploads its `tar.zst` as a GitHub Release asset, then fires a
`repository_dispatch(publish-plugin)` at this repo with
`{id, name, version, os, arch, url, sha256, size?, min_core?}`. The `publish`
workflow adds/replaces that `(id, version, os, arch)` entry in `index.json`,
signs it, and commits — Pages redeploys on push.

Manual publish: **Actions → "Publish plugin to registry" → Run workflow** with the
same fields.

## One-time setup (runbook)

1. `bash scripts/gen-key.sh` **locally** — prints the base64 private seed and
   public key. Never commit or paste the private seed.
2. Repo → Settings → Secrets → Actions → add **`REGISTRY_SIGNING_KEY`** = the
   base64 private seed.
3. Put the base64 public key in `public/pubkey.txt` and in every appliance's
   `[registry].public_key`.
4. Repo → Settings → Pages → Source = **GitHub Actions** (the `pages` workflow
   deploys `public/`).
5. Confirm `https://homeCore-io.github.io/registry/index.json` resolves.

The signature is over the **raw bytes** of `index.json` — never reformat it
between signing and serving, or verification fails.
