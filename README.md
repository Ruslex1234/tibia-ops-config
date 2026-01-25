# Tibia Ops Config

A comprehensive Tibia game operations management system that monitors enemy guilds, tracks player deaths, and maintains configuration lists. Data is automatically published to AWS S3 for consumption by external systems.

## Features

- **Enemy Death Tracking**: Monitors online members of enemy guilds and checks their death lists
- **Automatic Troll Detection**: Adds unguilded killers to the trolls list automatically
- **Name Normalization**: Ensures all names use proper Tibia capitalization
- **Case-Insensitive Duplicate Detection**: Prevents duplicate entries regardless of case
- **World Guild Data**: Fetches and maintains guild member lists for 14 Tibia worlds
- **S3 Publishing**: Combines all configs into a single JSON and uploads to AWS S3

## Repository Structure

```
tibia-ops-config/
├── scripts/                          # Python scripts
│   ├── config.py                     # Centralized configuration
│   ├── tibia_api.py                  # Shared TibiaData API client
│   ├── check_online_enemies.py       # Enemy death tracker
│   └── gen_worlds_guilds.py          # World guilds data generator
├── .configs/                         # Configuration files
│   ├── trolls.json                   # Tracked troll players
│   ├── bastex.json                   # Bastex guild tracking list
│   ├── block.json                    # Blocked players list
│   ├── alerts.json                   # Alert players list
│   └── world_guilds_data.json        # Auto-generated guild data
├── .github/workflows/                # GitHub Actions
│   ├── check_online_enemies.yml      # Runs every 10 min
│   ├── guilds_data.yml               # Runs every 10 min
│   └── publish-configs-to-s3.yml     # Publishes to S3
└── README.md
```

## Configuration

All configuration is centralized in `scripts/config.py`:

```python
# Enemy guilds to monitor (guild_name -> world)
ENEMY_GUILDS = {
    "Bastex": "Firmera",
    "Bastex Ruzh": "Tempestera"
}

# Worlds to fetch guild data from
WORLDS = [
    'Quidera', 'Firmera', 'Aethera', 'Monstera', 'Talera',
    'Lobera', 'Quintera', 'Wintera', 'Eclipta', 'Epoca',
    'Zunera', 'Mystera', 'Xymera', 'Tempestera'
]
```

To add or change enemy guilds, simply edit the `ENEMY_GUILDS` dictionary.

## Pipelines

### 1. Check Online Enemies (`check_online_enemies.yml`)

**Schedule**: Every 10 minutes

**What it does**:
1. Fetches online members from configured enemy guilds
2. Checks each online member's death list via TibiaData API
3. For each player killer in the deaths:
   - Checks if they're on the same server
   - Checks if they have no guild affiliation
   - If both conditions met, adds them to `trolls.json`
4. Automatically normalizes names to proper Tibia capitalization
5. Detects and corrects case-insensitive duplicates

**Example output**:
```
[Bastex] (Firmera)
  Found 3 online member(s)

  Checking deaths for: Enemy Player
    Found 5 death(s)
    Found 2 unique player killer(s)
      [New Troll] Checking... ADDING (unguilded on Firmera)
        [NORMALIZED] Using correct name: 'New Troll'

Summary
============================================================
Initial trolls count: 112
New trolls added: 1
Names normalized: 0
Final trolls count: 113
```

### 2. Generate Guilds Data (`guilds_data.yml`)

**Schedule**: Every 10 minutes

**What it does**:
1. Fetches active guild lists for all 14 configured worlds
2. For each guild, fetches the member list
3. Saves data to `.configs/world_guilds_data.json`
4. Preserves old data if API fetches fail (resilient to outages)

### 3. Publish Configs to S3 (`publish-configs-to-s3.yml`)

**Schedule**: On changes to `.configs/` or manual trigger

**What it does**:
1. Combines all `.configs/*.json` files into a single `combined_config.json`
2. Compares with existing S3 object (byte-comparison)
3. Only uploads if content has changed
4. Uses GitHub OIDC for secure AWS authentication (no static keys)

## Configuration Files

| File | Description |
|------|-------------|
| `trolls.json` | Players identified as "trolls" (unguilded killers from death lists) |
| `bastex.json` | Manual tracking list for Bastex-related players |
| `block.json` | Players to block/ignore |
| `alerts.json` | Players that trigger alerts |
| `world_guilds_data.json` | Auto-generated: All guild members by world |

## Setup

### Prerequisites

- Python 3.9+
- GitHub repository with Actions enabled
- AWS account (for S3 publishing)

### GitHub Secrets/Variables Required

| Name | Type | Description |
|------|------|-------------|
| `GH_PAT` | Secret | GitHub Personal Access Token for pushing changes |
| `S3_BUCKET` | Variable/Secret | S3 bucket name |
| `AWS_ROLE_ARN` | Variable/Secret | IAM role ARN for OIDC |
| `AWS_REGION` | Variable | AWS region (default: `us-east-1`) |

### AWS IAM Role Setup

Create an IAM role with GitHub OIDC trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*"
        }
      }
    }
  ]
}
```

Attach a permissions policy for S3:

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
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::YOUR_BUCKET/configs/*"
    }
  ]
}
```

## Running Locally

```bash
# Check online enemies and update trolls.json
python scripts/check_online_enemies.py

# Generate world guilds data
python scripts/gen_worlds_guilds.py
```

## API Reference

The scripts use the [TibiaData API v4](https://tibiadata.com/):

- `GET /v4/character/{name}` - Character info, deaths, guild
- `GET /v4/guild/{name}` - Guild members and online status
- `GET /v4/guilds/{world}` - List of active guilds for a world

All API calls include:
- Exponential backoff retry (2s, 4s, 8s, 16s) for transient errors
- 30-second timeout per request
- Gzip compression support

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `AccessDenied` on S3 | Verify `AWS_ROLE_ARN` and IAM policy permissions |
| `Unable to locate credentials` | Ensure OIDC is configured correctly |
| API rate limits | The retry logic handles this automatically |
| Duplicate entries | The script detects case-insensitive duplicates |

### Checking Logs

View workflow logs in GitHub Actions to see:
- Which enemies were online
- Deaths processed
- New trolls added
- Names normalized

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally with `python scripts/<script>.py`
5. Submit a pull request

## License

This project is for personal/educational use for Tibia game operations management.
