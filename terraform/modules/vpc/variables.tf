variable "name" {
  description = "Stable name prefix for this VPC."
  type        = string
}

variable "vpc_cidr" {
  description = "IPv4 CIDR assigned to the VPC."
  type        = string
}

variable "peer_vpc_cidr" {
  description = "Approved peer VPC CIDR allowed by the healthy baseline NACL."
  type        = string
}

variable "workload_role" {
  description = "VPC role in the approved source-to-destination TCP/443 path."
  type        = string

  validation {
    condition     = contains(["source", "destination"], var.workload_role)
    error_message = "workload_role must be source or destination."
  }
}

variable "destination_port" {
  description = "Approved destination port for the healthy path."
  type        = number
  default     = 443
}

variable "availability_zones" {
  description = "Two approved Availability Zones."
  type        = list(string)

  validation {
    condition     = length(var.availability_zones) == 2
    error_message = "Exactly two Availability Zones are required."
  }
}

variable "private_subnet_cidrs" {
  description = "Two private subnet CIDRs aligned with availability_zones."
  type        = list(string)

  validation {
    condition     = length(var.private_subnet_cidrs) == 2
    error_message = "Exactly two private subnet CIDRs are required."
  }
}

variable "enable_flow_logs" {
  description = "Create VPC Flow Logs only for a controlled diagnostic session."
  type        = bool
  default     = false
}

variable "flow_log_retention_days" {
  description = "CloudWatch retention for controlled-session VPC Flow Logs."
  type        = number
  default     = 7
}

variable "tags" {
  description = "Additional ownership and cost-allocation tags."
  type        = map(string)
  default     = {}
}
