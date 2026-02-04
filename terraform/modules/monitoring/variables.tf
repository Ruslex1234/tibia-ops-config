# =============================================================================
# Monitoring Module Variables
# =============================================================================

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "config_bucket_name" {
  description = "Name of the S3 config bucket"
  type        = string
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
  default     = ""
}
