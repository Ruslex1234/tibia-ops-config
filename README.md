# Tibia Ops Config

A Tibia game operations management system built with a full **DevSecOps CI/CD pipeline**. Monitors enemy guilds, tracks player deaths, maintains configuration lists, and deploys to AWS S3 -- all with automated testing, security scanning, and staged deployments.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Repository Structure](#repository-structure)
- [The CI/CD Pipeline Explained](#the-cicd-pipeline-explained)
  - [What is CI/CD?](#what-is-cicd)
  - [The Developer Workflow (SDLC)](#the-developer-workflow-sdlc)
  - [CI Pipeline - Continuous Integration](#ci-pipeline---continuous-integration)
  - [CD Pipeline - Continuous Deployment](#cd-pipeline---continuous-deployment)
  - [Scheduled Jobs](#scheduled-jobs)
- [DevSecOps Practices](#devsecops-practices)
  - [What is DevSecOps?](#what-is-devsecops)
  - [Security Tools Used](#security-tools-used)
  - [Shift Left Security](#shift-left-security)
- [Branch Protection & Git Flow](#branch-protection--git-flow)
- [Tools Reference](#tools-reference)
- [Setup Guide](#setup-guide)
- [Running Locally](#running-locally)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
Developer                  GitHub                        AWS
─────────                  ──────                        ───

  Write code ──────> Push to feature branch
                           │
                     Open Pull Request
                           │
                    ┌──────┴──────┐
                    │ CI PIPELINE │  (automated gate)
                    ├─────────────┤
                    │ 1. Lint     │  flake8 - code style
                    │ 2. Test     │  pytest - unit tests
                    │ 3. Security │  bandit, pip-audit, gitleaks
                    │ 4. Validate │  JSON config check
                    └──────┬──────┘
                           │
                    All stages pass? ──No──> Fix & re-push
                           │
                          Yes
                           │
                    Merge to main
                           │
                    ┌──────┴──────┐
                    │ CD PIPELINE │  (automated deploy)
                    ├─────────────┤
                    │ 1. Build    │  compile + quick test
                    │ 2. Package  │  combine configs
                    │ 3. Staging  │  dry-run validation
                    │ 4. Deploy   │  upload to S3 ──────────> S3 Bucket
                    │ 5. Smoke    │  verify deployment ─────> S3 Bucket
                    └─────────────┘

                    ┌──────────────────┐
                    │ SCHEDULED JOBS   │  (every 10 min)
                    ├──────────────────┤
                    │ Guild Data Fetch │  TibiaData API ────> .configs/
                    │ Enemy Tracker    │  TibiaData API ────> .configs/
                    └──────────────────┘
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
│   └── test_check_online_enemies.py     #   Enemy tracker tests
│
├── .configs/                            # Data files (deployed to S3)
│   ├── trolls.json                      #   Auto-updated troll list
│   ├── bastex.json                      #   Guild tracking list
│   ├── block.json                       #   Blocked players
│   ├── alerts.json                      #   Alert players
│   └── world_guilds_data.json           #   Auto-generated guild data
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                       #   CI Pipeline (PRs)
│   │   ├── cd.yml                       #   CD Pipeline (deploy)
│   │   ├── scheduled-jobs.yml           #   Scheduled data collection
│   │   └── publish-configs-to-s3.yml    #   Legacy S3 publisher
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

## The CI/CD Pipeline Explained

### What is CI/CD?

**CI/CD** stands for **Continuous Integration / Continuous Deployment**. It's the practice of automatically building, testing, and deploying code every time a change is made.

| Term | What It Means | When It Runs |
|------|---------------|--------------|
| **CI** (Continuous Integration) | Automatically test every code change | On every Pull Request |
| **CD** (Continuous Delivery) | Automatically prepare code for release | After merging to main |
| **CD** (Continuous Deployment) | Automatically deploy to production | After delivery succeeds |

**Why?** Without CI/CD, developers manually test and deploy code, which is slow, error-prone, and inconsistent. CI/CD automates this so every change goes through the same quality gates.

---

### The Developer Workflow (SDLC)

The **Software Development Life Cycle (SDLC)** in this project follows these steps:

```
1. PLAN        →  Decide what to build (issue/ticket)
2. CODE        →  Write code on a feature branch
3. BUILD       →  Pre-commit hooks run locally
4. TEST        →  CI pipeline runs automated tests
5. SECURE      →  Security scanners check for vulnerabilities
6. REVIEW      →  Code review via Pull Request
7. MERGE       →  Merge to main after approval
8. DEPLOY      →  CD pipeline deploys to production
9. MONITOR     →  Scheduled jobs keep data fresh
```

Here's how that maps to our tools:

```
Step        Tool/Process              File
────        ────────────              ────
PLAN        GitHub Issues             n/a
CODE        Git + feature branches    n/a
BUILD       pre-commit hooks          .pre-commit-config.yaml
TEST        pytest                    tests/
SECURE      bandit + pip-audit        .github/workflows/ci.yml
REVIEW      GitHub PR + CODEOWNERS    .github/CODEOWNERS
MERGE       Branch protection rules   GitHub Settings
DEPLOY      GitHub Actions → S3       .github/workflows/cd.yml
MONITOR     Scheduled jobs            .github/workflows/scheduled-jobs.yml
```

---

### CI Pipeline - Continuous Integration

**File:** `.github/workflows/ci.yml`
**Triggers:** Every Pull Request to `main`

The CI pipeline has **4 stages** that run in order. If any stage fails, the pipeline stops and the PR is blocked from merging.

```
┌─────────────────────────────────────────────────────────────┐
│                    CI PIPELINE                              │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐   │
│  │  STAGE 1 │    │  STAGE 2 │    │      STAGE 3         │   │
│  │   LINT   │───>│   TEST   │    │     SECURITY         │   │
│  │ (flake8) │    │ (pytest) │    │ (bandit + pip-audit  │   │
│  └──────────┘    └──────────┘    │  + gitleaks)         │   │
│       │               │          └──────────────────────┘   │
│       │               │                    │                │
│       └───────────────┴────────────────────┘                │
│                        │                                    │
│                  ┌──────────┐                                │
│                  │  STAGE 4 │                                │
│                  │ VALIDATE │                                │
│                  │  (JSON)  │                                │
│                  └──────────┘                                │
│                        │                                    │
│                  ┌──────────┐                                │
│                  │CI PASSED │ ← Branch protection checks    │
│                  └──────────┘   this status                 │
└─────────────────────────────────────────────────────────────┘
```

#### Stage 1: Lint (flake8)

**What:** Checks code style against PEP 8 standards.
**Why:** Consistent code style makes code easier to read and review.
**Tool:** [flake8](https://flake8.pycqa.org) - a Python linting tool.

```bash
# Run locally:
flake8 scripts/ tests/ --config .flake8
```

Catches things like:
- Lines that are too long (>120 chars)
- Unused imports
- Undefined variables
- Missing whitespace

#### Stage 2: Test (pytest)

**What:** Runs all unit tests and generates a coverage report.
**Why:** Verifies code behaves correctly before merging.
**Tool:** [pytest](https://pytest.org) - Python's most popular test framework.

```bash
# Run locally:
pytest tests/ --verbose --cov=scripts
```

Our tests use **mocking** (`unittest.mock`) to simulate API responses so tests run fast and don't hit the real TibiaData API.

#### Stage 3: Security Scan

**What:** Scans for security vulnerabilities in code and dependencies.
**Why:** Catches security issues before they reach production.
**Tools:**

| Tool | Type | What It Does |
|------|------|--------------|
| [bandit](https://bandit.readthedocs.io) | **SAST** | Scans Python source code for security anti-patterns (hardcoded passwords, eval(), insecure HTTP) |
| [pip-audit](https://github.com/pypa/pip-audit) | **SCA** | Checks installed packages against known vulnerability databases (CVEs) |
| [gitleaks](https://github.com/gitleaks/gitleaks) | **Secrets** | Scans git history for accidentally committed API keys, passwords, tokens |

```bash
# Run locally:
bandit -r scripts/ -c .bandit          # SAST scan
pip-audit                               # Dependency scan
```

#### Stage 4: Validate Configs

**What:** Validates all JSON configuration files are syntactically valid.
**Why:** A broken JSON file would crash the application at runtime.

---

### CD Pipeline - Continuous Deployment

**File:** `.github/workflows/cd.yml`
**Triggers:** Push to `main` (after PR merge)

The CD pipeline takes validated code and deploys it to production through **5 stages**:

```
┌─────────────────────────────────────────────────────────────┐
│                    CD PIPELINE                              │
│                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────────────────┐   │
│  │  STAGE 1 │───>│  STAGE 2 │───>│      STAGE 3         │   │
│  │  BUILD   │    │ PACKAGE  │    │  DEPLOY STAGING      │   │
│  │          │    │          │    │  (dry-run)            │   │
│  └──────────┘    └──────────┘    └──────────────────────┘   │
│                                            │                │
│                                  ┌──────────────────────┐   │
│                                  │      STAGE 4         │   │
│                                  │  DEPLOY PRODUCTION   │   │
│                                  │  (S3 upload)         │   │
│                                  └──────────────────────┘   │
│                                            │                │
│                                  ┌──────────────────────┐   │
│                                  │      STAGE 5         │   │
│                                  │    SMOKE TEST        │   │
│                                  │  (verify deploy)     │   │
│                                  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

#### Stage 1: Build
Compiles all Python scripts, runs a quick test suite, generates build metadata (commit SHA, timestamp).

#### Stage 2: Package
Combines all `.configs/*.json` files into a single `combined_config.json` artifact with a SHA256 checksum. This artifact is uploaded to GitHub Actions and reused in every subsequent stage (**"build once, deploy many"** principle).

#### Stage 3: Deploy Staging (dry-run)
Downloads the artifact, verifies its integrity (SHA256 check), and validates the JSON structure contains all required keys. No actual deployment happens - this is a safety check.

#### Stage 4: Deploy Production
Authenticates to AWS using **OIDC** (no static keys), downloads the existing S3 object for byte-comparison, and only uploads if content has changed. This avoids unnecessary writes.

#### Stage 5: Smoke Test
After deployment, downloads the deployed object from S3 and verifies it's valid and contains all required configuration keys. This is the final safety net.

---

### Scheduled Jobs

**File:** `.github/workflows/scheduled-jobs.yml`
**Triggers:** Every 10 minutes (cron)

These are **operational jobs** that run independently of the CI/CD pipeline. They collect live data from the TibiaData API.

| Job | What It Does | Output |
|-----|--------------|--------|
| `update-guild-data` | Fetches guild member lists for 14 Tibia worlds | `world_guilds_data.json` |
| `check-enemies` | Monitors enemy guild deaths, adds unguilded killers to troll list | `trolls.json` |

---

## DevSecOps Practices

### What is DevSecOps?

**DevSecOps** = Development + Security + Operations. It means security is integrated into every stage of the development process, not bolted on at the end.

```
Traditional:    Plan → Code → Test → Deploy → Security Audit (too late!)

DevSecOps:      Plan → Code → Security → Test → Security → Deploy → Security
                              ↑ pre-commit    ↑ CI scan     ↑ runtime
                              hooks           pipeline       monitoring
```

### Security Tools Used

| Layer | Tool | Stage | What It Does |
|-------|------|-------|--------------|
| **Local** | pre-commit | Before commit | Runs linters, security checks, secrets detection before code leaves your machine |
| **SAST** | bandit | CI Pipeline | Static Application Security Testing - scans source code for vulnerability patterns |
| **SCA** | pip-audit | CI Pipeline | Software Composition Analysis - checks dependencies for known CVEs |
| **Secrets** | gitleaks | CI Pipeline | Scans git history for accidentally committed secrets (API keys, passwords) |
| **Config** | JSON validate | CI Pipeline | Ensures config files are syntactically valid |
| **Infra** | OIDC | CD Pipeline | Uses temporary credentials instead of static AWS keys |
| **Review** | CODEOWNERS | GitHub | Requires specific people to approve changes to sensitive files |
| **Integrity** | SHA256 | CD Pipeline | Verifies artifacts aren't tampered with between stages |

### Shift Left Security

**"Shift Left"** means catching security issues as early as possible in the development process (moving them "left" on the timeline):

```
                    ← SHIFT LEFT ←

                    Cheapest to fix              Most expensive to fix
                    ──────────────               ────────────────────
Pre-commit          CI Pipeline        Staging        Production
┌─────────┐        ┌──────────┐       ┌──────┐       ┌──────────┐
│ gitleaks │        │ bandit   │       │ dry- │       │ smoke    │
│ flake8   │        │ pip-audit│       │ run  │       │ test     │
│ bandit   │        │ gitleaks │       │      │       │          │
│ JSON     │        │ pytest   │       │      │       │          │
└─────────┘        └──────────┘       └──────┘       └──────────┘
    ↑                   ↑                ↑                ↑
  Seconds           Minutes           Minutes          Seconds
  (on your          (on PR)           (on merge)       (post-deploy)
   machine)
```

---

## Branch Protection & Git Flow

### Branching Strategy

```
main (protected)
  │
  ├── feature/add-new-guild      ← New features
  ├── fix/duplicate-detection    ← Bug fixes
  └── chore/update-dependencies  ← Maintenance
```

**Rules:**
1. `main` is **protected** - no direct pushes allowed
2. All changes go through **Pull Requests**
3. PRs require the **CI pipeline to pass** before merging
4. PRs require **CODEOWNER approval** for sensitive files
5. Branches are deleted after merge (keeps repo clean)

### Recommended Branch Protection Settings

Go to **Settings > Branches > Add rule** for `main`:

- [x] Require a pull request before merging
- [x] Require status checks to pass (select "CI Passed")
- [x] Require branches to be up to date
- [x] Require code owner reviews
- [x] Do not allow bypassing the above settings

### Git Workflow Example

```bash
# 1. Create a feature branch
git checkout -b feature/add-new-enemy-guild

# 2. Make your changes
vim scripts/config.py

# 3. Pre-commit hooks run automatically
git add .
git commit -m "Add new enemy guild"
# → pre-commit runs: flake8, bandit, gitleaks, JSON check

# 4. Push and open a PR
git push -u origin feature/add-new-enemy-guild
# → CI pipeline runs: lint, test, security, validate

# 5. Get review, merge to main
# → CD pipeline runs: build, package, stage, deploy, smoke test
```

---

## Tools Reference

### Open Source Tools Used

| Tool | Category | Purpose | Website |
|------|----------|---------|---------|
| **pytest** | Testing | Unit test framework | [pytest.org](https://pytest.org) |
| **pytest-cov** | Testing | Code coverage reporting | [pytest-cov.readthedocs.io](https://pytest-cov.readthedocs.io) |
| **pytest-mock** | Testing | Mocking library for tests | [pytest-mock.readthedocs.io](https://pytest-mock.readthedocs.io) |
| **flake8** | Linting | PEP 8 code style checker | [flake8.pycqa.org](https://flake8.pycqa.org) |
| **bandit** | SAST | Python security scanner | [bandit.readthedocs.io](https://bandit.readthedocs.io) |
| **pip-audit** | SCA | Dependency vulnerability scanner | [github.com/pypa/pip-audit](https://github.com/pypa/pip-audit) |
| **gitleaks** | Secrets | Git secrets scanner | [github.com/gitleaks/gitleaks](https://github.com/gitleaks/gitleaks) |
| **pre-commit** | Local CI | Git hook manager | [pre-commit.com](https://pre-commit.com) |
| **GitHub Actions** | CI/CD | Pipeline orchestrator | [github.com/features/actions](https://github.com/features/actions) |

### DevSecOps Terminology Glossary

| Term | Definition |
|------|-----------|
| **CI** | Continuous Integration - automatically build and test on every change |
| **CD** | Continuous Deployment - automatically deploy after tests pass |
| **SAST** | Static Application Security Testing - scan source code for vulnerabilities |
| **SCA** | Software Composition Analysis - scan dependencies for known CVEs |
| **SDLC** | Software Development Life Cycle - the phases code goes through |
| **OIDC** | OpenID Connect - authenticate without static credentials |
| **Shift Left** | Find issues earlier in the development process |
| **Pipeline** | Automated sequence of build/test/deploy steps |
| **Artifact** | A built/packaged file that moves through the pipeline |
| **Gate** | A checkpoint that must pass before proceeding |
| **Smoke Test** | Quick post-deploy test to verify basic functionality |
| **Branch Protection** | Rules preventing direct pushes to important branches |
| **CODEOWNERS** | File defining who must review changes to specific paths |
| **Pre-commit Hook** | Script that runs before each git commit |
| **Idempotent** | Can run multiple times with the same result (our S3 deploy) |
| **DRY** | Don't Repeat Yourself - our shared `tibia_api.py` module |
| **Environment** | A deployment target (staging, production) |
| **Concurrency** | Control to prevent parallel conflicting runs |

---

## Setup Guide

### Prerequisites

- Python 3.9+
- Git
- AWS account (for S3 publishing)
- GitHub repository with Actions enabled

### 1. Clone and Install

```bash
git clone https://github.com/Ruslex1234/tibia-ops-config.git
cd tibia-ops-config

# Install dev dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

### 2. GitHub Secrets/Variables

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `GH_PAT` | Secret | Yes | Personal Access Token for scheduled job commits |
| `AWS_ROLE_ARN` | Secret | Yes | IAM role ARN for OIDC authentication |
| `S3_BUCKET` | Variable | Yes | S3 bucket name |
| `AWS_REGION` | Variable | No | AWS region (default: `us-east-1`) |

### 3. AWS IAM Role Setup

Create an IAM role with GitHub OIDC trust policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
      "StringLike": { "token.actions.githubusercontent.com:sub": "repo:Ruslex1234/tibia-ops-config:*" }
    }
  }]
}
```

### 4. Enable Branch Protection

Go to **Settings > Branches > Add rule** for `main` and enable the checks listed in [Branch Protection](#branch-protection--git-flow).

---

## Running Locally

```bash
# Run the enemy death tracker
python scripts/check_online_enemies.py

# Run the guild data generator
python scripts/gen_worlds_guilds.py

# Run tests
pytest tests/ --verbose --cov=scripts

# Run linter
flake8 scripts/ tests/ --config .flake8

# Run security scan
bandit -r scripts/ -c .bandit

# Run all pre-commit hooks
pre-commit run --all-files
```

---

## Configuration

All configuration is centralized in `scripts/config.py`:

```python
ENEMY_GUILDS = {
    "Bastex": "Firmera",
    "Bastex Ruzh": "Tempestera"
}
```

To add a new enemy guild, edit this dictionary. To add a new world to monitor, add it to the `WORLDS` list. All changes go through the CI/CD pipeline via Pull Request.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CI lint fails | Run `flake8 scripts/ tests/` locally and fix style issues |
| CI tests fail | Run `pytest tests/ -v` locally to see which tests fail |
| Security scan flags issue | Check the bandit output for the specific rule and fix or add to `.bandit` skips |
| `AccessDenied` on S3 | Verify `AWS_ROLE_ARN` and IAM policy permissions |
| Scheduled job not running | Check GitHub Actions is enabled and cron syntax is correct |
| Pre-commit hook blocks commit | Run `pre-commit run --all-files` to see and fix all issues |
| Duplicate troll entries | The script handles this automatically with case-insensitive checks |
