# =============================================================================
# IAM Module Variables
# =============================================================================

variable "github_org" {
  description = "GitHub organization or username"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
}

variable "config_bucket_arn" {
  description = "ARN of the S3 config bucket"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}
