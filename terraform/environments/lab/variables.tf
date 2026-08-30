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
