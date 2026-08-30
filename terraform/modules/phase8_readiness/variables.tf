variable "name_prefix" {
  type        = string
  description = "Stable project/environment name prefix."
}

variable "region" {
  type        = string
  description = "Approved deployment region."
}

variable "account_id" {
  type        = string
  description = "AWS account ID that owns the Terraform-managed remediation resources."

  validation {
    condition     = can(regex("^[0-9]{12}$", var.account_id))
    error_message = "account_id must be exactly 12 decimal digits."
  }
}

variable "tags" {
  type        = map(string)
  description = "Required project ownership tags."
}

variable "authorized_approvers" {
  type        = list(string)
  description = "Explicit IAM principal ARNs authorized to submit approval decisions. Empty remains fail-closed."
  default     = []

  validation {
    condition     = length(distinct(var.authorized_approvers)) == length(var.authorized_approvers) && alltrue([for principal in var.authorized_approvers : can(regex("^arn:aws:iam::[0-9]{12}:(user|role)/.+$", principal))])
    error_message = "authorized_approvers must contain unique IAM principal ARNs."
  }
}

variable "destination_security_group_id" {
  type        = string
  description = "Terraform-managed destination workload security group."
}

variable "source_vpc_id" {
  type        = string
  description = "Terraform-managed source VPC used to bind remediation resource ownership."
}

variable "destination_vpc_id" {
  type        = string
  description = "Terraform-managed destination VPC."
}

variable "source_route_table_ids" {
  type        = list(string)
  description = "Terraform-managed source route tables."
}

variable "destination_route_table_ids" {
  type        = list(string)
  description = "Terraform-managed destination route tables."
}

variable "destination_network_acl_id" {
  type        = string
  description = "Terraform-managed destination private network ACL."
}

variable "approval_lambda_filename" {
  type        = string
  description = "Local deterministic Approval Lambda ZIP path."
}

variable "remediation_lambda_filename" {
  type        = string
  description = "Local deterministic Remediation Lambda ZIP path."
}
