# =============================================================================
# Terraform Main Configuration
# =============================================================================
# Infrastructure as Code for Tibia Ops Config
#
# This configuration provisions:
# - S3 bucket for config storage
# - IAM roles and policies for GitHub Actions OIDC
# - CloudWatch for monitoring and alerting
#
# Demonstrates:
# - Terraform best practices
# - Modular architecture
# - AWS security best practices
# - OIDC authentication (no static credentials)
# =============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state configuration (uncomment for production)
  # backend "s3" {
  #   bucket         = "tibia-ops-terraform-state"
  #   key            = "terraform.tfstate"
  #   region         = "us-east-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-locks"
  # }
}

# =============================================================================
# Provider Configuration
# =============================================================================

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "tibia-ops-config"
      Environment = var.environment
      ManagedBy   = "terraform"
      Repository  = "Ruslex1234/tibia-ops-config"
    }
  }
}

# =============================================================================
# Data Sources
# =============================================================================

data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

# =============================================================================
# Modules
# =============================================================================

# S3 Bucket for Config Storage
module "s3_config_bucket" {
  source = "./modules/s3"

  bucket_name         = var.config_bucket_name
  environment         = var.environment
  enable_versioning   = true
  enable_encryption   = true
  lifecycle_days      = 90
}

# IAM Roles for GitHub Actions OIDC
module "github_oidc" {
  source = "./modules/iam"

  github_org          = var.github_org
  github_repo         = var.github_repo
  config_bucket_arn   = module.s3_config_bucket.bucket_arn
  environment         = var.environment
}

# CloudWatch Monitoring (optional)
module "monitoring" {
  source = "./modules/monitoring"

  count = var.enable_monitoring ? 1 : 0

  environment         = var.environment
  config_bucket_name  = module.s3_config_bucket.bucket_name
  alert_email         = var.alert_email
}
