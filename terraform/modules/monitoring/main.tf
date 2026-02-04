# =============================================================================
# Monitoring Module - CloudWatch
# =============================================================================
# Creates CloudWatch resources for monitoring:
# - Log groups
# - Metric alarms
# - SNS topics for notifications
# =============================================================================

# -----------------------------------------------------------------------------
# SNS Topic for Alerts
# -----------------------------------------------------------------------------

resource "aws_sns_topic" "alerts" {
  name = "tibia-ops-alerts-${var.environment}"

  tags = {
    Name        = "tibia-ops-alerts"
    Environment = var.environment
  }
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# -----------------------------------------------------------------------------
# CloudWatch Log Group
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "github_actions" {
  name              = "/github-actions/tibia-ops-config"
  retention_in_days = 30

  tags = {
    Name        = "github-actions-logs"
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# CloudWatch Alarms
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_metric_alarm" "s3_4xx_errors" {
  alarm_name          = "tibia-ops-s3-4xx-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "4xxErrors"
  namespace           = "AWS/S3"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "S3 bucket is returning 4xx errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    BucketName = var.config_bucket_name
    FilterId   = "AllRequests"
  }

  tags = {
    Environment = var.environment
  }
}

resource "aws_cloudwatch_metric_alarm" "s3_5xx_errors" {
  alarm_name          = "tibia-ops-s3-5xx-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "5xxErrors"
  namespace           = "AWS/S3"
  period              = 300
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "S3 bucket is returning 5xx errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    BucketName = var.config_bucket_name
    FilterId   = "AllRequests"
  }

  tags = {
    Environment = var.environment
  }
}

# -----------------------------------------------------------------------------
# CloudWatch Dashboard
# -----------------------------------------------------------------------------

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "tibia-ops-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "S3 Request Metrics"
          region = "us-east-1"
          metrics = [
            ["AWS/S3", "AllRequests", "BucketName", var.config_bucket_name],
            ["AWS/S3", "GetRequests", "BucketName", var.config_bucket_name],
            ["AWS/S3", "PutRequests", "BucketName", var.config_bucket_name]
          ]
          period = 300
          stat   = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title  = "S3 Error Rates"
          region = "us-east-1"
          metrics = [
            ["AWS/S3", "4xxErrors", "BucketName", var.config_bucket_name],
            ["AWS/S3", "5xxErrors", "BucketName", var.config_bucket_name]
          ]
          period = 300
          stat   = "Sum"
        }
      }
    ]
  })
}
