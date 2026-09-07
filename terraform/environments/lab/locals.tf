locals {
  common_tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Project     = var.project_name
  }

  network_topology = {
    source = {
      vpc_cidr = "10.10.0.0/16"
      private_subnet_cidrs = [
        "10.10.10.0/24",
        "10.10.20.0/24",
      ]
    }
    destination = {
      vpc_cidr = "10.20.0.0/16"
      private_subnet_cidrs = [
        "10.20.10.0/24",
        "10.20.20.0/24",
      ]
    }
  }

  availability_zones = [
    "eu-west-1a",
    "eu-west-1b",
  ]

  healthy_path = {
    protocol         = "tcp"
    destination_port = 443
  }

  name_prefix = "${var.project_name}-${var.environment}"

  # Phase 6 controlled scenarios. Exactly one deterministic failure is injected per
  # non-healthy scenario using conditional attributes/counts on existing resources.
  #
  # These toggles change AWS configuration on `terraform apply` and therefore require a
  # later, separately authorized apply gate. Specifically:
  #   - broken_sg: mutates the destination SG ingress rule CIDR (SG rule change).
  #   - broken_route: deletes only the source->destination peering route resources
  #     (one direction). broken_peering deletes both directions. Both are recreated on
  #     restore; the aws_vpc_peering_connection itself is not deleted.
  #   - broken_nacl: CREATES a higher-priority deny NACL rule (allow rule is retained).
  #   - broken_peering: also changes the peering DNS-resolution options.
  # broken_dns is a local-only fixture flag (no Route 53 / AWS resource, no mutation).
  # IAM is never modified. VPC endpoints are not applicable and TGW is out of scope.
  # `healthy` (the default) restores every toggle to the approved baseline.
  scenario_effects = {
    healthy = {
      sg_source_cidr           = local.network_topology.source.vpc_cidr
      enable_source_route      = true
      enable_destination_route = true
      enable_deny_nacl         = false
      enable_peering_dns       = true
      dns_fixture_broken       = false
    }
    broken_sg = {
      # Destination ingress scoped to an unroutable CIDR: the approved source can
      # never match, deterministically blocking the application path.
      sg_source_cidr           = "192.0.2.0/32"
      enable_source_route      = true
      enable_destination_route = true
      enable_deny_nacl         = false
      enable_peering_dns       = true
      dns_fixture_broken       = false
    }
    broken_route = {
      # One direction only: disable the source->destination route; keep the return route.
      sg_source_cidr           = local.network_topology.source.vpc_cidr
      enable_source_route      = false
      enable_destination_route = true
      enable_deny_nacl         = false
      enable_peering_dns       = true
      dns_fixture_broken       = false
    }
    broken_nacl = {
      sg_source_cidr           = local.network_topology.source.vpc_cidr
      enable_source_route      = true
      enable_destination_route = true
      enable_deny_nacl         = true
      enable_peering_dns       = true
      dns_fixture_broken       = false
    }
    broken_dns = {
      sg_source_cidr           = local.network_topology.source.vpc_cidr
      enable_source_route      = true
      enable_destination_route = true
      enable_deny_nacl         = false
      enable_peering_dns       = true
      dns_fixture_broken       = true
    }
    broken_peering = {
      # Disable the whole path: delete both route directions AND disable cross-VPC DNS
      # resolution. The aws_vpc_peering_connection is retained; routes are recreated and
      # DNS re-enabled when restored to healthy.
      sg_source_cidr           = local.network_topology.source.vpc_cidr
      enable_source_route      = false
      enable_destination_route = false
      enable_deny_nacl         = false
      enable_peering_dns       = false
      dns_fixture_broken       = false
    }
  }

  active_scenario = local.scenario_effects[var.scenario]
}
