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

variable "enable_source_route" {
  description = <<-EOT
    Phase 6 toggle for the source->destination peering routes. Defaults to true
    (healthy). broken_route and broken_peering set this false, which deletes the
    Terraform-managed source route resources (recreated on restore). The peering
    connection is retained.
  EOT
  type        = bool
  default     = true
}

variable "enable_destination_route" {
  description = <<-EOT
    Phase 6 toggle for the destination->source (return) peering routes. Defaults to
    true (healthy). broken_peering sets this false; broken_route leaves it true so
    only one direction is disabled. Deleting these removes the Terraform-managed
    return route resources (recreated on restore).
  EOT
  type        = bool
  default     = true
}

variable "enable_dns_resolution" {
  description = <<-EOT
    Phase 6 toggle for cross-VPC DNS resolution on the peering connection. Defaults to
    true (healthy). broken_peering sets this false to further degrade the peering path
    without deleting resources.
  EOT
  type        = bool
  default     = true
}

variable "tags" {
  description = "Additional ownership and cost-allocation tags."
  type        = map(string)
  default     = {}
}
