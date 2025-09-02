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
