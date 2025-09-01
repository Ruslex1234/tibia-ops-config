# Config Publisher — Merge & Upload to S3 (No Repo Commits)

This workflow merges your config JSON files and the generated `world_guilds_data.json` into **one** canonical JSON, and uploads it to S3 **only when the content changes**. It uses **GitHub OIDC** to assume an AWS role (no static keys) and **does not commit** generated files back to the repo (keeps your history clean, cuts pointless CI time, and avoids extra S3 PUTs).

## What it does

- Runs every 10 minutes (to refresh guild data) and on pushes that touch configs.
- Executes `gen_worlds_guilds.py` to regenerate `.configs/world_guilds_data.json` locally.
- Reads all JSON under `.configs/` (also supports a legacy one-off file named `.configsbastex.json`).
- Builds a **single minified, sorted** JSON file `combined_config.json` with keys equal to the source filenames (minus `.json`), for example:
  ```json
  {
    "alerts": [...],
    "bastex": [...],
    "block": [...],
    "trolls": [...],
    "world_guilds_data": { "...": "..." }
  }
  ```
- Downloads the current S3 object and **byte-compares** it; if identical, **skips upload**. If different or missing, uploads with optional SSE/KMS.
- Never pushes any generated files to Git — you can delete your old GH_PAT and commit steps.

> **Tip:** For consistency, consider renaming `".configsbastex.json"` to `".configs/bastex.json"`. The workflow already supports both, but normalizing paths is cleaner.

## Repo layout (expected)

```
.configs/
  alerts.json
  block.json
  trolls.json
  bastex.json
  world_guilds_data.json   # created by the script each run (not committed)
gen_worlds_guilds.py
.github/workflows/publish-configs-to-s3.yml  # the workflow below
.github/workflows/guilds_data.yml # this commits world_guilds_data.json from gen_worlds_guilds.py
```

## Setup

1. **Create an IAM Role for GitHub OIDC** (one-time)

   Trust policy (replace `ORG/REPO` and branches as needed):

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": { "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com" },
         "Action": "sts:AssumeRoleWithWebIdentity",
         "Condition": {
           "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
           "StringLike": { "token.actions.githubusercontent.com:sub": "repo:ORG/REPO:*" }
         }
       }
     ]
   }
   ```

   Permissions policy (least-privileged S3 access to a single object path):

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": ["s3:ListBucket"],
         "Resource": "arn:aws:s3:::YOUR_BUCKET"
       },
       {
         "Effect": "Allow",
         "Action": ["s3:GetObject","s3:PutObject"],
         "Resource": "arn:aws:s3:::YOUR_BUCKET/configs/combined.json"
       }
     ]
   }
   ```

   You can widen to a prefix if needed (e.g., `arn:aws:s3:::YOUR_BUCKET/configs/*`).

2. **GitHub repo settings**

   - Set one of:
     - **Variable** `S3_BUCKET = YOUR_BUCKET`
     - **Secret**   `S3_BUCKET = YOUR_BUCKET`
   - Set one of:
     - **Variable** `AWS_ROLE_ARN = arn:aws:iam::<ACCOUNT_ID>:role/<ROLE_NAME>`
     - **Secret**   `AWS_ROLE_ARN = arn:aws:iam::<ACCOUNT_ID>:role/<ROLE_NAME>`
   - (Optional) Variables/Env:
     - `AWS_REGION` (default `us-east-1`)
     - `S3_KEY` (default `configs/combined.json`)
     - `S3_SSE` (`AES256` or `aws:kms`)
     - `S3_KMS_KEY_ID` (if using `aws:kms`)
     - `DRY_RUN` (`true` to test without uploading)

3. **Drop in the workflow**

   Save the YAML below as `.github/workflows/publish-configs-to-s3.yml` and commit it.

4. **(Optional) Enable S3 versioning**

   Versioning is helpful if you ever need to roll back a bad config quickly.

## Why this saves money/time

- **No pointless git commits** every 10 minutes.
- **Single S3 GET** per run to compare, and **PUT only on change**.
- **Minified, deterministic JSON** (sorted keys) makes the diff cheap and reliable.

## FAQs

- **What if the object doesn’t exist yet?** The first run uploads it.
- **What if I switch to KMS?** Still fine; we don’t rely on ETags/MD5 — we do a byte-comparison after downloading.
- **Can I publish to multiple keys/buckets?** Yes — duplicate the “Upload to S3” step with different `S3_KEY`/`S3_BUCKET` values.
- **How do I stop the 10‑minute schedule?** Remove or change the `schedule:` block. Push triggers will still work.

## Troubleshooting

- `AccessDenied` on S3: confirm `AWS_ROLE_ARN` is correct and the policy allows `GetObject/PutObject/ListBucket` on your path.
- `Unable to locate credentials`: OIDC role not assumed — ensure `permissions: id-token: write` and `role-to-assume` are set.
- `CONFIG_DIR does not exist`: ensure your `.configs/` folder exists in the repo, even if initially empty.
- API rate limits or timeouts: add basic backoff/retries inside `gen_worlds_guilds.py` if TibiaData occasionally throttles.

---

### The workflow file

Copy this into `.github/workflows/publish-configs-to-s3.yml`:

```yaml
name: Merge & publish configs to S3

on:
  workflow_dispatch:
  push:
    branches: [ main, master ]
    paths:
      - '.configs/**'
      - 'gen_worlds_guilds.py'
      - '.github/workflows/publish-configs-to-s3.yml'
  schedule:
    - cron: '*/10 * * * *'  # every 10 minutes (for fresh world_guilds_data.json)

permissions:
  id-token: write   # for GitHub OIDC to assume AWS role
  contents: read

env:
  AWS_REGION: us-east-1
  # Prefer a repo/org Variable, fall back to Secret. Set one of these in repo settings.
  S3_BUCKET: ${{ vars.S3_BUCKET || secrets.S3_BUCKET }}
  S3_KEY: configs/combined.json
  DRY_RUN: 'false'  # set to 'true' to preview without uploading
  CONFIG_DIR: .configs

  # Optional: enable server-side encryption
  # S3_SSE: AES256               # or aws:kms
  # S3_KMS_KEY_ID: your-kms-key  # when using aws:kms

concurrency:
  group: publish-configs-to-s3
  cancel-in-progress: true

jobs:
  publish:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN || vars.AWS_ROLE_ARN }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Verify AWS identity
        run: aws sts get-caller-identity

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Generate world_guilds_data.json (no repo commit)
        run: |
          set -euo pipefail
          python gen_worlds_guilds.py
          test -f "${CONFIG_DIR}/world_guilds_data.json"

      - name: Combine configs into single JSON
        id: combine
        shell: bash
        run: |
          set -euo pipefail
          python - << 'PY'
          import json, os, glob, sys, hashlib
          base = os.environ.get('CONFIG_DIR', '.configs')

          # Collect *.json under .configs plus legacy '.configs*.json' files
          paths = sorted(glob.glob(os.path.join(base, '*.json')))
          if os.path.exists('.configsbastex.json'):
            paths.append('.configsbastex.json')

          combined = {}
          for p in paths:
            # derive key from filename (strip leading dot/config path and .json)
            fname = os.path.basename(p)
            key = fname[:-5] if fname.endswith('.json') else fname
            with open(p, 'r', encoding='utf-8') as f:
              try:
                combined[key] = json.load(f)
              except Exception as e:
                raise SystemExit(f"Failed to parse JSON in {p}: {e}")

          # Minified & stable (sorted keys) for cheap diffs
          payload = json.dumps(combined, sort_keys=True, separators=(',', ':')).encode('utf-8')
          out = 'combined_config.json'
          with open(out, 'wb') as f:
            f.write(payload)

          # Write a SHA256 for logs/debug
          sha = hashlib.sha256(payload).hexdigest()
          open('combined.sha256','w').write(sha)
          print("Combined keys:", ",".join(sorted(combined.keys())))
          print("SHA256:", sha)
          print("Bytes:", len(payload))
          PY
          echo "path=combined_config.json" >> "$GITHUB_OUTPUT"

      - name: Diff against S3 (skip upload if identical)
        id: diff
        shell: bash
        env:
          BUCKET: ${{ env.S3_BUCKET }}
          KEY: ${{ env.S3_KEY }}
        run: |
          set -euo pipefail

          # Try to download existing object (ignore if missing)
          if aws s3 cp "s3://${BUCKET}/${KEY}" existing.json --only-show-errors; then
            :
          else
            echo "no_remote=true" >> "$GITHUB_OUTPUT"
            echo "changed=true"    >> "$GITHUB_OUTPUT"
            exit 0
          fi

          # Compare bytes exactly
          if cmp -s "combined_config.json" "existing.json"; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
            echo "reason=No changes detected" >> "$GITHUB_OUTPUT"
          else
            echo "changed=true" >> "$GITHUB_OUTPUT"
            echo "reason=Content differs from S3" >> "$GITHUB_OUTPUT"
          fi

      - name: Upload to S3 (only if changed)
        if: steps.diff.outputs.changed == 'true' && env.DRY_RUN != 'true'
        env:
          BUCKET: ${{ env.S3_BUCKET }}
          KEY: ${{ env.S3_KEY }}
        run: |
          set -euo pipefail
          EXTRA_ARGS=()
          if [ -n "${S3_SSE:-}" ]; then EXTRA_ARGS+=(--sse "${S3_SSE}"); fi
          if [ -n "${S3_KMS_KEY_ID:-}" ]; then EXTRA_ARGS+=(--sse-kms-key-id "${S3_KMS_KEY_ID}"); fi
          aws s3 cp "combined_config.json" "s3://${BUCKET}/${KEY}"             --only-show-errors             --content-type application/json             --metadata commit="${GITHUB_SHA}"             "${EXTRA_ARGS[@]}"
          echo "Uploaded to s3://${BUCKET}/${KEY}"

      - name: Skip notice (unchanged or dry-run)
        if: steps.diff.outputs.changed != 'true' || env.DRY_RUN == 'true'
        run: |
          echo "No upload performed. DRY_RUN=${DRY_RUN} changed=${{ steps.diff.outputs.changed || 'false' }} reason='${{ steps.diff.outputs.reason || 'n/a' }}'"

```
