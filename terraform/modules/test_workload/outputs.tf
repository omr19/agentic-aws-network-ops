output "instance_id" {
  description = "Short-lived EC2 endpoint identifier."
  value       = aws_instance.this.id
}

output "network_interface_id" {
  description = "Primary ENI used by Reachability Analyzer."
  value       = aws_instance.this.primary_network_interface_id
}

output "private_ip" {
  description = "Private IPv4 address of the test endpoint."
  value       = aws_instance.this.private_ip
}

output "security_group_id" {
  description = "Workload security-group identifier."
  value       = aws_security_group.this.id
}
