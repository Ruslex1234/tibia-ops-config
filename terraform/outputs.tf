# =============================================================================
# Terraform Outputs
# =============================================================================
# Output values for the Tibia Ops Config infrastructure
# =============================================================================

# -----------------------------------------------------------------------------
# S3 Outputs
# -----------------------------------------------------------------------------

output "config_bucket_name" {
  description = "Name of the S3 config bucket"
  value       = module.s3_config_bucket.bucket_name
}

output "config_bucket_arn" {
  description = "ARN of the S3 config bucket"
  value       = module.s3_config_bucket.bucket_arn
}

output "config_bucket_domain" {
  description = "Domain name of the S3 config bucket"
  value       = module.s3_config_bucket.bucket_domain_name
}

# -----------------------------------------------------------------------------
# IAM Outputs
# -----------------------------------------------------------------------------

output "github_actions_role_arn" {
  description = "ARN of the IAM role for GitHub Actions"
  value       = module.github_oidc.role_arn
}

output "github_actions_role_name" {
  description = "Name of the IAM role for GitHub Actions"
  value       = module.github_oidc.role_name
}

# -----------------------------------------------------------------------------
# Account Information
# -----------------------------------------------------------------------------

output "aws_account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "aws_region" {
  description = "AWS Region"
  value       = data.aws_region.current.name
}

# -----------------------------------------------------------------------------
# GitHub Actions Configuration
# -----------------------------------------------------------------------------

output "github_actions_config" {
  description = "Configuration values for GitHub Actions secrets"
  value = {
    aws_region        = data.aws_region.current.name
    aws_role_arn      = module.github_oidc.role_arn
    s3_bucket         = module.s3_config_bucket.bucket_name
  }
}
