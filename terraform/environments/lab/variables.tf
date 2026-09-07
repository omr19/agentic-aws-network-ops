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

variable "enable_phase8_readiness" {
  description = "Opt in to the tagged Phase 8 approval table, Lambda functions, log groups, and separate execution roles. AgentCore and invocation policies remain excluded."
  type        = bool
  default     = false
}

variable "phase8_account_id" {
  description = "AWS account ID that owns Phase 8 remediation resources; required when readiness is enabled and kept empty otherwise."
  type        = string
  default     = ""

  validation {
    condition     = var.phase8_account_id == "" || can(regex("^[0-9]{12}$", var.phase8_account_id))
    error_message = "phase8_account_id must be empty or exactly 12 decimal digits."
  }
}

variable "phase8_authorized_approvers" {
  description = "Explicit IAM principal ARNs authorized to submit Phase 8 approval decisions; empty remains fail-closed."
  type        = list(string)
  default     = []

  validation {
    condition     = length(distinct(var.phase8_authorized_approvers)) == length(var.phase8_authorized_approvers) && alltrue([for principal in var.phase8_authorized_approvers : can(regex("^arn:aws:iam::[0-9]{12}:(user|role)/.+$", principal))])
    error_message = "phase8_authorized_approvers must contain unique IAM principal ARNs."
  }
}

variable "scenario" {
  description = <<-EOT
    Phase 6 controlled network scenario. `healthy` is the approved baseline (default).
    Each `broken_*` value injects exactly one deterministic failure and MUTATES AWS
    configuration on `terraform apply`, requiring a separately authorized apply gate:
      - broken_sg: changes the destination security-group ingress CIDR.
      - broken_route / broken_peering: set the peering route count to 0, which
        deletes the Terraform-managed peering route resources (recreated on restore);
        the VPC peering connection itself is retained.
      - broken_nacl: creates a temporary higher-priority NACL deny rule (the healthy
        allow rule is retained).
      - broken_peering: also disables cross-VPC DNS resolution on the peering options.
    broken_dns is a local-only fixture flag (no AWS resource, no mutation). Restoring
    `healthy` recreates the baseline. VPC-endpoint failures are not applicable (no
    project VPC endpoints are deployed) and Transit Gateway is out of scope.
  EOT
  type        = string
  default     = "healthy"

  validation {
    condition = contains([
      "healthy",
      "broken_sg",
      "broken_route",
      "broken_nacl",
      "broken_dns",
      "broken_peering",
    ], var.scenario)
    error_message = "scenario must be one of: healthy, broken_sg, broken_route, broken_nacl, broken_dns, broken_peering."
  }
}
