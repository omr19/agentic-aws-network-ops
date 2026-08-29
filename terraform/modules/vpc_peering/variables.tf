variable "name" {
  description = "Stable name for the peering connection."
  type        = string
}

variable "source_vpc_id" {
  description = "Requester/source VPC identifier."
  type        = string
}

variable "source_vpc_cidr" {
  description = "Requester/source VPC CIDR."
  type        = string
}

variable "source_route_table_ids" {
  description = "Source private route tables requiring a route to the destination."
  type        = list(string)
}

variable "destination_vpc_id" {
  description = "Accepter/destination VPC identifier."
  type        = string
}

variable "destination_vpc_cidr" {
  description = "Accepter/destination VPC CIDR."
  type        = string
}

variable "destination_route_table_ids" {
  description = "Destination private route tables requiring a return route."
  type        = list(string)
}

variable "tags" {
  description = "Additional ownership and cost-allocation tags."
  type        = map(string)
  default     = {}
}
