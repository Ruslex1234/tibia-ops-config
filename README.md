# Tibia Ops Config

A Tibia game operations management system built with a full **DevSecOps CI/CD pipeline**. Monitors enemy guilds, tracks player deaths, maintains configuration lists, and deploys to AWS S3 -- all with automated testing, security scanning, staged deployments, **Prometheus/Grafana monitoring**, and **Infrastructure as Code with Terraform**.

[![CI Status](https://github.com/Ruslex1234/tibia-ops-config/actions/workflows/ci.yml/badge.svg)](https://github.com/Ruslex1234/tibia-ops-config/actions/workflows/ci.yml)
[![CD Status](https://github.com/Ruslex1234/tibia-ops-config/actions/workflows/cd.yml/badge.svg)](https://github.com/Ruslex1234/tibia-ops-config/actions/workflows/cd.yml)
[![Scheduled Jobs](https://github.com/Ruslex1234/tibia-ops-config/actions/workflows/scheduled-jobs.yml/badge.svg)](https://github.com/Ruslex1234/tibia-ops-config/actions/workflows/scheduled-jobs.yml)

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Repository Structure](#repository-structure)
- [Observability Stack](#observability-stack)
  - [Prometheus Metrics](#prometheus-metrics)
  - [Grafana Dashboards](#grafana-dashboards)
  - [Docker Compose](#docker-compose)
- [Infrastructure as Code](#infrastructure-as-code)
  - [Terraform Modules](#terraform-modules)
  - [AWS Resources](#aws-resources)
- [The CI/CD Pipeline Explained](#the-cicd-pipeline-explained)
  - [What is CI/CD?](#what-is-cicd)
  - [CI Pipeline - Continuous Integration](#ci-pipeline---continuous-integration)
  - [CD Pipeline - Continuous Deployment](#cd-pipeline---continuous-deployment)
  - [Scheduled Jobs](#scheduled-jobs)
- [DevSecOps Practices](#devsecops-practices)
- [GitHub Pages Dashboard](#github-pages-dashboard)
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
│                                                                                │           │
│   OBSERVABILITY STACK                                                          ▼           │
│   ───────────────────                                           ┌─────────────────────┐    │
│                                                                 │       AWS           │    │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │  ┌───────────────┐  │    │
│   │    App      │────▶│ Prometheus  │────▶│   Grafana   │       │  │   S3 Bucket   │  │    │
│   │  (metrics)  │     │ (collect)   │     │ (visualize) │       │  │   (configs)   │  │    │
│   └─────────────┘     └─────────────┘     └─────────────┘       │  └───────────────┘  │    │
│         │                                                       │          ▲          │    │
│   ┌─────┴─────┐                                                 │   ┌──────┴──────┐   │    │
│   │  Docker   │                                                 │   │ IAM + OIDC  │   │    │
│   │ Compose   │                                                 │   │ (no creds)  │   │    │
│   └───────────┘                                                 │   └─────────────┘   │    │
│                                                                 └─────────────────────┘    │
│                                                                                            │
│   INFRASTRUCTURE AS CODE                           GITHUB PAGES                            │
│   ──────────────────────                          ─────────────                            │
│                                                                                            │
│   ┌─────────────┐     ┌─────────────┐            ┌─────────────────────┐                   │
│   │  Terraform  │────▶│  AWS IAM    │            │  DevSecOps Dashboard│                   │
│   │  Modules    │     │  S3, OIDC   │            │  • Pipeline metrics │                   │
│   │  • s3       │     │  CloudWatch │            │  • Security scans   │                   │
│   │  • iam      │     └─────────────┘            │  • Test coverage    │                   │
│   │  • monitor  │                                └─────────────────────┘                   │
│   └─────────────┘                                                                          │
│                                                                                            │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Run the Full Stack Locally

```bash
# Clone the repository
git clone https://github.com/Ruslex1234/tibia-ops-config.git
cd tibia-ops-config

# Start the monitoring stack (App + Prometheus + Grafana)
docker-compose up -d

# Access the dashboards:
# Grafana:    http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
# App:        http://localhost:8000/metrics
```

### Run Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

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
│   ├── gen_worlds_guilds.py             #   World guild data generator
│   └── metrics_server.py                #   Prometheus metrics endpoint
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
├── monitoring/                          # Observability stack
│   ├── prometheus/
│   │   ├── prometheus.yml               #   Prometheus configuration
│   │   └── alerts.yml                   #   Alerting rules
│   └── grafana/
│       ├── provisioning/                #   Auto-provisioning configs
│       └── dashboards/                  #   Pre-built dashboards
│
├── terraform/                           # Infrastructure as Code
│   ├── main.tf                          #   Root module
│   ├── variables.tf                     #   Input variables
│   ├── outputs.tf                       #   Output values
│   ├── modules/
│   │   ├── s3/                          #   S3 bucket module
│   │   ├── iam/                         #   IAM + OIDC module
│   │   └── monitoring/                  #   CloudWatch module
│   └── environments/
│       ├── dev/                         #   Dev environment vars
│       └── prod/                        #   Prod environment vars
│
├── docs/                                # GitHub Pages dashboard
│   ├── index.html                       #   Dashboard HTML
│   ├── assets/
│   │   ├── css/style.css                #   Dashboard styles
│   │   └── js/dashboard.js              #   Dashboard logic
│   └── data/metrics.json                #   Dashboard metrics data
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                       #   CI Pipeline (PRs)
│   │   ├── cd.yml                       #   CD Pipeline (deploy)
│   │   ├── scheduled-jobs.yml           #   Scheduled data collection
│   │   └── update-dashboard.yml         #   Dashboard metrics updater
│   ├── pull_request_template.md         #   PR template
│   └── CODEOWNERS                       #   Required reviewers
│
├── Dockerfile                           # Container image
├── docker-compose.yml                   # Full observability stack
├── .pre-commit-config.yaml              # Pre-commit hooks
├── .flake8                              # Linter configuration
├── .bandit                              # Security scanner config
├── requirements.txt                     # Production dependencies
├── requirements-dev.txt                 # Dev/test dependencies
└── README.md                            # This file
```

---

## Observability Stack

### Prometheus Metrics

The application exposes Prometheus metrics at `http://localhost:8000/metrics`:

| Metric | Type | Description |
|--------|------|-------------|
| `tibia_trolls_total` | Gauge | Total players in trolls list |
| `tibia_bastex_total` | Gauge | Total players in bastex list |
| `tibia_enemies_online` | Gauge | Currently online enemies |
| `tibia_api_calls_total` | Counter | Total API calls made |
| `tibia_api_errors_total` | Counter | Total API errors |
| `tibia_guild_online_members` | Gauge | Online members per guild |
| `tibia_last_check_duration_seconds` | Gauge | Duration of last check |

### Grafana Dashboards

Pre-built dashboards are automatically provisioned:

- **Tibia Ops Overview** - Main operational dashboard
  - Troll list growth over time
  - Enemy online counts
  - API health metrics
  - Per-guild statistics

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Rebuild after code changes
docker-compose build --no-cache
docker-compose up -d
```

**Services:**

| Service | Port | Description |
|---------|------|-------------|
| `app` | 8000 | Metrics server |
| `prometheus` | 9090 | Metrics collection |
| `grafana` | 3000 | Visualization (admin/admin) |

---

## Infrastructure as Code

### Terraform Modules

| Module | Purpose | Resources Created |
|--------|---------|-------------------|
| `s3` | Config storage | S3 bucket with versioning, encryption, lifecycle |
| `iam` | GitHub OIDC auth | OIDC provider, IAM role, policies |
| `monitoring` | AWS monitoring | CloudWatch alarms, SNS topics, dashboard |

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
│                          │  • CloudWatch   │                    │
│                          └────────┬────────┘                    │
│                                   │                             │
│  ┌─────────────────┐              │      ┌─────────────────┐    │
│  │   S3 Bucket     │◀─────────────┘      │  CloudWatch     │    │
│  │  • Versioning   │                     │  • Alarms       │    │
│  │  • Encryption   │                     │  • Dashboard    │    │
│  │  • Lifecycle    │                     │  • SNS Topics   │    │
│  └─────────────────┘                     └─────────────────┘    │
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

## GitHub Pages Dashboard

A live dashboard displaying pipeline metrics, security scan results, and application statistics.

**Features:**
- CI/CD pipeline success rates
- Security scan visualizations
- Application metrics (trolls, bastex, enemies online)
- Architecture diagrams
- Quick start guides

**Access:** `https://ruslex1234.github.io/tibia-ops-config/`

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
| **Docker** | Containers | Application packaging |
| **Prometheus** | Monitoring | Metrics collection |
| **Grafana** | Monitoring | Visualization |
| **Terraform** | IaC | Infrastructure provisioning |
| **GitHub Actions** | CI/CD | Pipeline orchestration |

---

## Setup Guide

### Prerequisites

- Python 3.9+
- Docker & Docker Compose
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
# Start monitoring stack
docker-compose up -d

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
| Docker build fails | Run `docker-compose build --no-cache` |
| Grafana no data | Wait 30s for first scrape, check Prometheus targets |
| Terraform error | Run `terraform init` and check AWS credentials |
