variable "name" {
  description = "Stable name for the short-lived workload."
  type        = string
}

variable "role" {
  description = "Workload role in the approved TCP/443 path."
  type        = string

  validation {
    condition     = contains(["source", "destination"], var.role)
    error_message = "role must be source or destination."
  }
}

variable "vpc_id" {
  description = "VPC containing the workload."
  type        = string
}

variable "subnet_id" {
  description = "Private subnet containing the workload."
  type        = string
}

variable "peer_vpc_cidr" {
  description = "Peer VPC CIDR used to scope the TCP/443 security-group rule."
  type        = string
}

variable "ami_id" {
  description = "Approved Amazon Linux 2023 x86_64 AMI identifier."
  type        = string
}

variable "instance_type" {
  description = "Small instance type for the short-lived lab endpoint."
  type        = string
  default     = "t3.nano"

  validation {
    condition     = var.instance_type == "t3.nano"
    error_message = "The Phase 4 cost guardrail permits only t3.nano."
  }
}

variable "destination_port" {
  description = "Approved destination port."
  type        = number
  default     = 443
}

variable "user_data" {
  description = "Bootstrap script for the endpoint role."
  type        = string
}

variable "tags" {
  description = "Additional ownership and cost-allocation tags."
  type        = map(string)
  default     = {}
}
