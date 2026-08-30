variable "name_prefix" {
  type        = string
  description = "Stable project/environment name prefix."
}

variable "region" {
  type        = string
  description = "Approved deployment region."
}

variable "tags" {
  type        = map(string)
  description = "Required project ownership tags."
}

variable "destination_security_group_id" {
  type        = string
  description = "Terraform-managed destination workload security group."
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
