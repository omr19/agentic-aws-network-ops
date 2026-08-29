variable "aws_region" {
  description = "AWS Region approved for the lab."
  type        = string
  default     = "eu-west-1"

  validation {
    condition     = var.aws_region == "eu-west-1"
    error_message = "The approved MVP Region is eu-west-1."
  }
}

variable "project_name" {
  description = "Stable project identifier used in names and tags."
  type        = string
  default     = "agentic-aws-network-ops"

  validation {
    condition     = var.project_name == "agentic-aws-network-ops"
    error_message = "The project_name must remain agentic-aws-network-ops."
  }
}

variable "environment" {
  description = "Single MVP environment selected by ADR 015."
  type        = string
  default     = "lab"

  validation {
    condition     = var.environment == "lab"
    error_message = "Only the lab environment is approved for the MVP."
  }
}

variable "enable_flow_logs" {
  description = "Enable VPC Flow Logs only for controlled diagnostic/demo sessions."
  type        = bool
  default     = false
}

variable "flow_log_retention_days" {
  description = "Approved CloudWatch Logs retention for controlled VPC Flow Logs."
  type        = number
  default     = 7

  validation {
    condition     = var.flow_log_retention_days == 7
    error_message = "The approved VPC Flow Logs retention is seven days."
  }
}
