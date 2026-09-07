output "vpc_id" {
  description = "VPC identifier."
  value       = aws_vpc.this.id
}

output "vpc_arn" {
  description = "VPC ARN."
  value       = aws_vpc.this.arn
}

output "private_subnet_ids" {
  description = "Private subnet IDs in input order."
  value       = [for key in sort(keys(local.subnet_map)) : aws_subnet.private[key].id]
}

output "private_route_table_ids" {
  description = "Private route-table IDs in input order."
  value       = [for key in sort(keys(local.subnet_map)) : aws_route_table.private[key].id]
}

output "private_network_acl_id" {
  description = "Private subnet network ACL identifier."
  value       = aws_network_acl.private.id
}
