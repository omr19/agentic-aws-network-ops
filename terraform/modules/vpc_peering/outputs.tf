output "vpc_peering_connection_id" {
  description = "Identifier of the replaceable VPC peering interconnect."
  value       = aws_vpc_peering_connection.this.id
}

output "source_route_ids" {
  description = "Source-to-destination peering route identifiers."
  value       = aws_route.source_to_destination[*].id
}

output "destination_route_ids" {
  description = "Destination-to-source peering route identifiers."
  value       = aws_route.destination_to_source[*].id
}
