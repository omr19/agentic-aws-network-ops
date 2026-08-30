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

output "network_resource_ids" {
  description = "Identifiers used for inventory and deterministic diagnostics."
  value = {
    destination_network_acl_id = module.destination_vpc.private_network_acl_id
    destination_route_tables   = module.destination_vpc.private_route_table_ids
    destination_subnets        = module.destination_vpc.private_subnet_ids
    destination_vpc_id         = module.destination_vpc.vpc_id
    peering_connection_id      = module.vpc_peering.vpc_peering_connection_id
    source_network_acl_id      = module.source_vpc.private_network_acl_id
    source_route_tables        = module.source_vpc.private_route_table_ids
    source_subnets             = module.source_vpc.private_subnet_ids
    source_vpc_id              = module.source_vpc.vpc_id
  }
}

output "test_workload_ids" {
  description = "Short-lived workload and ENI identifiers for verification."
  value = {
    destination_instance_id = module.destination_workload.instance_id
    destination_eni_id      = module.destination_workload.network_interface_id
    destination_private_ip  = module.destination_workload.private_ip
    destination_sg_id       = module.destination_workload.security_group_id
    source_instance_id      = module.source_workload.instance_id
    source_eni_id           = module.source_workload.network_interface_id
    source_private_ip       = module.source_workload.private_ip
    source_sg_id            = module.source_workload.security_group_id
  }
}

output "reachability_analyzer_path_id" {
  description = "Network Insights Path used for Source-to-Destination TCP/443 analysis."
  value       = aws_ec2_network_insights_path.source_to_destination_https.id
}

output "phase8_readiness" {
  description = "Opt-in Phase 8 readiness resources; null when disabled."
  value = var.enable_phase8_readiness ? {
    approval_table_name         = module.phase8_readiness[0].approval_table_name
    approval_table_arn          = module.phase8_readiness[0].approval_table_arn
    approval_lambda_role_arn    = module.phase8_readiness[0].approval_lambda_role_arn
    remediation_lambda_role_arn = module.phase8_readiness[0].remediation_lambda_role_arn
  } : null
}

output "active_scenario" {
  description = "Phase 6 controlled scenario and its deterministic injection signature."
  value = {
    scenario                 = var.scenario
    sg_source_cidr           = local.active_scenario.sg_source_cidr
    enable_source_route      = local.active_scenario.enable_source_route
    enable_destination_route = local.active_scenario.enable_destination_route
    enable_deny_nacl         = local.active_scenario.enable_deny_nacl
    enable_peering_dns       = local.active_scenario.enable_peering_dns
    dns_fixture_broken       = local.active_scenario.dns_fixture_broken
    vpc_endpoints            = "not_applicable_no_project_endpoints"
    transit_gateway          = "out_of_scope"
  }
}
