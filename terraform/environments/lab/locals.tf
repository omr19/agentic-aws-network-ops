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
}
