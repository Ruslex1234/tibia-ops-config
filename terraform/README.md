# Terraform Infrastructure

This directory contains Infrastructure as Code (IaC) for the Tibia Ops Config project using Terraform.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         AWS Infrastructure                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐ │
│  │  GitHub Actions │────▶│   IAM Role      │────▶│   S3 Bucket   │ │
│  │     (OIDC)      │     │  (Assume Role)  │     │   (Configs)   │ │
│  └─────────────────┘     └─────────────────┘     └───────────────┘ │
│          │                       │                       │          │
│          │                       │                       │          │
│          ▼                       ▼                       ▼          │
│  ┌─────────────────┐     ┌─────────────────┐     ┌───────────────┐ │
│  │  OIDC Provider  │     │  IAM Policies   │     │  CloudWatch   │ │
│  │   (Trust)       │     │  (S3 Access)    │     │  (Monitoring) │ │
│  └─────────────────┘     └─────────────────┘     └───────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Module Structure

```
terraform/
├── main.tf                 # Root module - orchestrates all modules
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── modules/
│   ├── s3/                 # S3 bucket for config storage
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── iam/                # IAM roles and policies for GitHub OIDC
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── monitoring/         # CloudWatch alarms and dashboards
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
└── environments/
    ├── dev/
    │   └── terraform.tfvars
    └── prod/
        └── terraform.tfvars
```

## Prerequisites

1. **AWS CLI** configured with appropriate credentials
2. **Terraform** >= 1.5.0 installed

## Quick Start

### Initialize Terraform

```bash
cd terraform
terraform init
```

### Plan (Dev Environment)

```bash
terraform plan -var-file=environments/dev/terraform.tfvars
```

### Apply (Dev Environment)

```bash
terraform apply -var-file=environments/dev/terraform.tfvars
```

### Plan (Production)

```bash
terraform plan -var-file=environments/prod/terraform.tfvars
```

## Security Features

### OIDC Authentication (No Static Credentials)

This setup uses GitHub's OIDC provider to authenticate with AWS, eliminating the need for long-lived AWS access keys:

1. GitHub Actions requests an OIDC token
2. AWS validates the token against the OIDC provider
3. AWS issues temporary credentials via AssumeRoleWithWebIdentity
4. Credentials expire automatically after the workflow

### S3 Security

- **Encryption**: Server-side encryption with AES-256
- **Versioning**: Enabled for recovery and audit trail
- **Public Access**: Completely blocked
- **HTTPS Only**: Bucket policy enforces TLS

### IAM Least Privilege

- Roles are scoped to specific repositories
- Policies grant minimal required permissions
- No wildcard actions or resources

## Outputs

After applying, you'll get:

| Output | Description |
|--------|-------------|
| `config_bucket_name` | S3 bucket name for configs |
| `github_actions_role_arn` | IAM role ARN for GitHub Actions |
| `github_actions_config` | Ready-to-use GitHub secrets values |

## Cleanup

```bash
terraform destroy -var-file=environments/dev/terraform.tfvars
```

## Interview Talking Points

1. **Why Terraform?** - Declarative IaC, state management, provider ecosystem
2. **Why OIDC?** - No static credentials, automatic rotation, audit trail
3. **Why Modules?** - Reusability, separation of concerns, testability
4. **Why Remote State?** - Team collaboration, locking, encryption
