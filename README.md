# Tibia Ops Config

A Tibia game operations management system built with a **DevSecOps CI/CD pipeline**. Monitors enemy guilds, tracks player deaths, maintains configuration lists, and deploys to AWS S3 -- all with automated testing, security scanning, staged deployments, and **Infrastructure as Code with Terraform**.

[![CI Status](https://github.com/Ruslex1234/tibia-ops-config/actions/workflows/ci.yml/badge.svg)](https://github.com/Ruslex1234/tibia-ops-config/actions/workflows/ci.yml)
[![CD Status](https://github.com/Ruslex1234/tibia-ops-config/actions/workflows/cd.yml/badge.svg)](https://github.com/Ruslex1234/tibia-ops-config/actions/workflows/cd.yml)
[![Scheduled Jobs](https://github.com/Ruslex1234/tibia-ops-config/actions/workflows/scheduled-jobs.yml/badge.svg)](https://github.com/Ruslex1234/tibia-ops-config/actions/workflows/scheduled-jobs.yml)

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Repository Structure](#repository-structure)
- [Infrastructure as Code](#infrastructure-as-code)
  - [Terraform Modules](#terraform-modules)
  - [AWS Resources](#aws-resources)
- [The CI/CD Pipeline Explained](#the-cicd-pipeline-explained)
  - [What is CI/CD?](#what-is-cicd)
  - [CI Pipeline - Continuous Integration](#ci-pipeline---continuous-integration)
  - [CD Pipeline - Continuous Deployment](#cd-pipeline---continuous-deployment)
  - [Scheduled Jobs](#scheduled-jobs)
- [DevSecOps Practices](#devsecops-practices)
- [Guild Explorer (GitHub Pages)](#guild-explorer-github-pages)
- [Branch Protection & Git Flow](#branch-protection--git-flow)
- [Tools Reference](#tools-reference)
- [Setup Guide](#setup-guide)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────────────────────────┐
│                           TIBIA OPS CONFIG - FULL ARCHITECTURE                             │
├────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                            │
│   DEVELOPER WORKFLOW                           GITHUB ACTIONS                              │
│   ─────────────────                            ──────────────                              │
│                                                                                            │
│   ┌──────────────┐                    ┌─────────────────────────────────┐                  │
│   │   Developer  │────commit────────▶ │         CI PIPELINE             │                  │
│   │   (local)    │                    │  ┌─────┐ ┌─────┐ ┌──────────┐   │                  │
│   └──────────────┘                    │  │Lint │→│Test │→│Security  │   │                  │
│         │                             │  └─────┘ └─────┘ │(SAST/SCA)│   │                  │
│   ┌─────┴─────┐                       │                  └──────────┘   │                  │
│   │Pre-commit │                       └───────────────┬─────────────────┘                  │
│   │  Hooks    │                                       │                                    │
│   │ • flake8  │                                       ▼ (merge)                            │
│   │ • bandit  │                       ┌─────────────────────────────────┐                  │
│   │ • gitleaks│                       │         CD PIPELINE             │                  │
│   └───────────┘                       │  ┌─────┐ ┌───────┐ ┌─────────┐  │                  │
│                                       │  │Build│→│Package│→│ Deploy  │──┼──────┐           │
│                                       │  └─────┘ └───────┘ │ to S3   │  │      │           │
│                                       │                    └─────────┘  │      │           │
│                                       └─────────────────────────────────┘      │           │
│                                                                                ▼           │
│   SCHEDULED JOBS                                                ┌─────────────────────┐    │
│   ──────────────                                                │       AWS           │    │
│                                                                 │  ┌───────────────┐  │    │
│   ┌─────────────┐     ┌─────────────┐                           │  │   S3 Bucket   │  │    │
│   │ TibiaData   │────▶│  .configs/  │                           │  │   (configs)   │  │    │
│   │    API      │     │  JSON data  │                           │  └───────────────┘  │    │
│   └─────────────┘     └──────┬──────┘                           │          ▲          │    │
│                              │                                  │   ┌──────┴──────┐   │    │
│                              │                                  │   │ IAM + OIDC  │   │    │
│                              │                                  │   │ (no creds)  │   │    │
│                              │                                  │   └─────────────┘   │    │
│                              │                                  └─────────────────────┘    │
│   INFRASTRUCTURE AS CODE     │                     GITHUB PAGES                            │
│   ──────────────────────     │                    ─────────────                            │
│                              │                                                             │
│   ┌─────────────┐     ┌──────┴──────┐            ┌─────────────────────┐                   │
│   │  Terraform  │────▶│  AWS IAM    │            │   Guild Explorer    │                   │
│   │  Modules    │     │  S3, OIDC   │            │  • World → Guild    │                   │
│   │  • s3       │     └─────────────┘            │  • Member lookup    │                   │
│   │  • iam      │                                └─────────────────────┘                   │
│   └─────────────┘                                                                          │
│                                                                                            │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Run Locally

```bash
# Clone the repository
git clone https://github.com/Ruslex1234/tibia-ops-config.git
cd tibia-ops-config

# Install dev dependencies (the scripts themselves need only the stdlib)
pip install -r requirements-dev.txt

# Refresh guild data for all configured worlds
python scripts/gen_worlds_guilds.py

# Run the enemy death tracker
python scripts/check_online_enemies.py
```

### Run Tests

```bash
# Run tests with coverage
pytest tests/ -v --cov=scripts

# Run security scans
bandit -r scripts/ -c .bandit
pip-audit
```

### Deploy Infrastructure with Terraform

```bash
cd terraform
terraform init
terraform plan -var-file=environments/dev/terraform.tfvars
terraform apply -var-file=environments/dev/terraform.tfvars
```

---

## Repository Structure

```
tibia-ops-config/
│
├── scripts/                             # Application code
│   ├── config.py                        #   Centralized configuration
│   ├── tibia_api.py                     #   Shared API client (DRY principle)
│   ├── check_online_enemies.py          #   Enemy death tracker
│   └── gen_worlds_guilds.py             #   World guild data generator
│
├── tests/                               # Unit tests (pytest)
│   ├── conftest.py                      #   Shared test fixtures
│   ├── test_config.py                   #   Config validation tests
│   ├── test_tibia_api.py                #   API client tests (mocked)
│   ├── test_check_online_enemies.py     #   Enemy tracker tests
│   └── test_gen_worlds_guilds.py        #   Guild data generator tests
│
├── .configs/                            # Data files (deployed to S3)
│   ├── trolls.json                      #   Auto-updated troll list
│   ├── bastex.json                      #   Guild tracking list
│   ├── block.json                       #   Blocked players
│   ├── alerts.json                      #   Alert players
│   └── world_guilds_data.json           #   Auto-generated guild data
│
├── terraform/                           # Infrastructure as Code
│   ├── main.tf                          #   Root module
│   ├── variables.tf                     #   Input variables
│   ├── outputs.tf                       #   Output values
│   ├── modules/
│   │   ├── s3/                          #   S3 bucket module
│   │   └── iam/                         #   IAM + OIDC module
│   └── environments/
│       ├── dev/                         #   Dev environment vars
│       └── prod/                        #   Prod environment vars
│
├── docs/                                # GitHub Pages site (Guild Explorer)
│   ├── index.html                       #   Guild Explorer page
│   ├── assets/
│   │   ├── css/style.css                #   Styles
│   │   └── js/guilds.js                 #   World/guild/member lookup logic
│   └── data/
│       └── world_guilds_data.json       #   Minified mirror of .configs/ copy
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                       #   CI Pipeline (PRs)
│   │   ├── cd.yml                       #   CD Pipeline (deploy)
│   │   ├── publish-configs-to-s3.yml    #   Config publishing to S3
│   │   └── scheduled-jobs.yml           #   Scheduled data collection
│   ├── pull_request_template.md         #   PR template
│   └── CODEOWNERS                       #   Required reviewers
│
├── .pre-commit-config.yaml              # Pre-commit hooks
├── .flake8                              # Linter configuration
├── .bandit                              # Security scanner config
├── requirements.txt                     # Production dependencies
├── requirements-dev.txt                 # Dev/test dependencies
└── README.md                            # This file
```

---

## Infrastructure as Code

### Terraform Modules

| Module | Purpose | Resources Created |
|--------|---------|-------------------|
| `s3` | Config storage | S3 bucket with versioning, encryption, lifecycle |
| `iam` | GitHub OIDC auth | OIDC provider, IAM role, policies |

### AWS Resources

```
┌─────────────────────────────────────────────────────────────────┐
│                      Terraform Managed                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐     ┌─────────────────┐                    │
│  │  OIDC Provider  │────▶│   IAM Role      │                    │
│  │  (GitHub)       │     │  (Trust Policy) │                    │
│  └─────────────────┘     └────────┬────────┘                    │
│                                   │                             │
│                          ┌────────┴────────┐                    │
│                          │   IAM Policies  │                    │
│                          │  • S3 access    │                    │
│                          └────────┬────────┘                    │
│                                   │                             │
│  ┌─────────────────┐              │                             │
│  │   S3 Bucket     │◀─────────────┘                             │
│  │  • Versioning   │                                            │
│  │  • Encryption   │                                            │
│  │  • Lifecycle    │                                            │
│  └─────────────────┘                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Deploy with Terraform

```bash
cd terraform

# Initialize
terraform init

# Plan (dev)
terraform plan -var-file=environments/dev/terraform.tfvars

# Apply (dev)
terraform apply -var-file=environments/dev/terraform.tfvars

# Outputs
terraform output github_actions_config
```

---

## The CI/CD Pipeline Explained

### What is CI/CD?

**CI/CD** stands for **Continuous Integration / Continuous Deployment**. It's the practice of automatically building, testing, and deploying code every time a change is made.

| Term | What It Means | When It Runs |
|------|---------------|--------------|
| **CI** (Continuous Integration) | Automatically test every code change | On every Pull Request |
| **CD** (Continuous Delivery) | Automatically prepare code for release | After merging to main |
| **CD** (Continuous Deployment) | Automatically deploy to production | After delivery succeeds |

### CI Pipeline - Continuous Integration

**File:** `.github/workflows/ci.yml`

```
┌─────────────────────────────────────────────────────────────┐
│                    CI PIPELINE                              │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐   │
│  │  STAGE 1 │    │  STAGE 2 │    │      STAGE 3         │   │
│  │   LINT   │───>│   TEST   │───>│     SECURITY         │   │
│  │ (flake8) │    │ (pytest) │    │ (bandit + pip-audit  │   │
│  └──────────┘    └──────────┘    │  + gitleaks)         │   │
│       │               │          └──────────────────────┘   │
│       │               │                    │                │
│       └───────────────┴────────────────────┘                │
│                        │                                    │
│                  ┌──────────┐                               │
│                  │  STAGE 4 │                               │
│                  │ VALIDATE │                               │
│                  │  (JSON)  │                               │
│                  └──────────┘                               │
│                        │                                    │
│                  ┌──────────┐                               │
│                  │CI PASSED │ ← Branch protection checks    │
│                  └──────────┘   this status                 │
└─────────────────────────────────────────────────────────────┘
```

### CD Pipeline - Continuous Deployment

**File:** `.github/workflows/cd.yml`

```
┌─────────────────────────────────────────────────────────────┐
│                    CD PIPELINE                              │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐   │
│  │  STAGE 1 │───>│  STAGE 2 │───>│      STAGE 3         │   │
│  │  BUILD   │    │ PACKAGE  │    │  DEPLOY STAGING      │   │
│  │          │    │ + SHA256 │    │  (dry-run)           │   │
│  └──────────┘    └──────────┘    └──────────────────────┘   │
│                                            │                │
│                                  ┌──────────────────────┐   │
│                                  │      STAGE 4         │   │
│                                  │  DEPLOY PRODUCTION   │   │
│                                  │  (OIDC → S3)         │   │
│                                  └──────────────────────┘   │
│                                            │                │
│                                  ┌──────────────────────┐   │
│                                  │      STAGE 5         │   │
│                                  │    SMOKE TEST        │   │
│                                  │  (verify deploy)     │   │
│                                  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Scheduled Jobs

**File:** `.github/workflows/scheduled-jobs.yml`

| Job | What It Does | Output | Schedule |
|-----|--------------|--------|----------|
| `update-guild-data` | Fetches guild lists for 14 worlds | `world_guilds_data.json` | Every 10 min |
| `check-enemies` | Monitors deaths, adds unguilded killers | `trolls.json` | Every 10 min |

`update-guild-data` also writes a minified mirror of the guild data to
`docs/data/world_guilds_data.json` in the same commit, since GitHub Pages
serves `docs/` and cannot read `.configs/`.

---

## DevSecOps Practices

### Security Tools

| Layer | Tool | Stage | What It Does |
|-------|------|-------|--------------|
| **Local** | pre-commit | Before commit | Runs linters, security checks before push |
| **SAST** | bandit | CI Pipeline | Scans source code for vulnerabilities |
| **SCA** | pip-audit | CI Pipeline | Checks dependencies for known CVEs |
| **Secrets** | gitleaks | CI Pipeline | Scans for accidentally committed secrets |
| **Infra** | OIDC | CD Pipeline | No static AWS credentials |
| **Review** | CODEOWNERS | GitHub | Requires approval for sensitive files |
| **Integrity** | SHA256 | CD Pipeline | Verifies artifacts between stages |

### Shift Left Security

```
                    ← SHIFT LEFT ←

                    Cheapest to fix              Most expensive to fix
                    ──────────────               ────────────────────
Pre-commit          CI Pipeline        Staging        Production
┌─────────┐        ┌──────────┐       ┌──────┐       ┌──────────┐
│ gitleaks│        │ bandit   │       │ dry- │       │ smoke    │
│ flake8  │        │ pip-audit│       │ run  │       │ test     │
│ bandit  │        │ gitleaks │       │      │       │          │
└─────────┘        └──────────┘       └──────┘       └──────────┘
```

---

## Guild Explorer (GitHub Pages)

A static page for looking up guild members by world.

**Features:**
- Pick a world, then a guild, to list that guild's members
- "All guilds" option lists every member in a world, labelled by guild
- Live text filter over member names
- Selection is mirrored into the query string, so views are shareable
  (e.g. `?world=Firmera&guild=Amerans`)

**Access:** `https://ruslex1234.github.io/tibia-ops-config/`

**Data source:** `docs/data/world_guilds_data.json`, a minified mirror of
`.configs/world_guilds_data.json` refreshed by the `update-guild-data`
scheduled job. Pages publishes `main:/docs`, so the site cannot read
`.configs/` directly.

---

## Branch Protection & Git Flow

```
main (protected)
  │
  ├── feature/add-new-guild      ← New features
  ├── fix/duplicate-detection    ← Bug fixes
  └── chore/update-dependencies  ← Maintenance
```

**Rules:**
1. `main` is **protected** - no direct pushes
2. All changes go through **Pull Requests**
3. PRs require **CI pipeline to pass**
4. PRs require **CODEOWNER approval**

---

## Tools Reference

| Tool | Category | Purpose |
|------|----------|---------|
| **pytest** | Testing | Unit test framework |
| **flake8** | Linting | Code style checker |
| **bandit** | SAST | Security scanner |
| **pip-audit** | SCA | Dependency scanner |
| **gitleaks** | Secrets | Git secrets scanner |
| **pre-commit** | Local CI | Git hook manager |
| **Terraform** | IaC | Infrastructure provisioning |
| **GitHub Actions** | CI/CD | Pipeline orchestration |

---

## Setup Guide

### Prerequisites

- Python 3.9+
- Terraform >= 1.5.0
- AWS CLI (for deployment)

### 1. Clone and Install

```bash
git clone https://github.com/Ruslex1234/tibia-ops-config.git
cd tibia-ops-config

pip install -r requirements-dev.txt
pip install pre-commit
pre-commit install
```

### 2. GitHub Secrets

| Name | Type | Description |
|------|------|-------------|
| `GH_PAT` | Secret | Personal Access Token |
| `AWS_ROLE_ARN` | Secret | IAM role for OIDC |
| `S3_BUCKET` | Variable | S3 bucket name |

### 3. Run Locally

```bash
# Run tests
pytest tests/ -v

# Run enemy tracker
python scripts/check_online_enemies.py
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CI lint fails | Run `flake8 scripts/ tests/` locally |
| CI tests fail | Run `pytest tests/ -v` locally |
| Security scan flags | Check bandit output, add to `.bandit` skips if false positive |
| S3 AccessDenied | Verify `AWS_ROLE_ARN` and IAM policy |
| Guild Explorer shows stale data | Wait for the next `update-guild-data` run, or trigger it manually |
| Terraform error | Run `terraform init` and check AWS credentials |
