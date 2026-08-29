output "deployment_context" {
  description = "Non-sensitive identifiers for the approved MVP environment."
  value = {
    environment = var.environment
    project     = var.project_name
    region      = var.aws_region
  }
}

output "approved_network_cidrs" {
  description = "Approved VPC and private-subnet CIDRs used by later module calls."
  value       = local.network_topology
}

output "healthy_connectivity_path" {
  description = "Approved protocol and destination port for the healthy MVP path."
  value       = local.healthy_path
}

output "flow_logs_configuration" {
  description = "Controlled-session Flow Logs defaults approved in Phase 2."
  value = {
    enabled        = var.enable_flow_logs
    retention_days = var.flow_log_retention_days
  }
}
