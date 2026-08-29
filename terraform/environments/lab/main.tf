data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "root-device-type"
    values = ["ebs"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

module "source_vpc" {
  source = "../../modules/vpc"

  availability_zones      = local.availability_zones
  destination_port        = local.healthy_path.destination_port
  enable_flow_logs        = var.enable_flow_logs
  flow_log_retention_days = var.flow_log_retention_days
  name                    = "${local.name_prefix}-source-vpc"
  peer_vpc_cidr           = local.network_topology.destination.vpc_cidr
  private_subnet_cidrs    = local.network_topology.source.private_subnet_cidrs
  vpc_cidr                = local.network_topology.source.vpc_cidr
  workload_role           = "source"
  tags = {
    Component = "source-network"
  }
}

module "destination_vpc" {
  source = "../../modules/vpc"

  availability_zones      = local.availability_zones
  destination_port        = local.healthy_path.destination_port
  enable_flow_logs        = var.enable_flow_logs
  flow_log_retention_days = var.flow_log_retention_days
  name                    = "${local.name_prefix}-destination-vpc"
  peer_vpc_cidr           = local.network_topology.source.vpc_cidr
  private_subnet_cidrs    = local.network_topology.destination.private_subnet_cidrs
  vpc_cidr                = local.network_topology.destination.vpc_cidr
  workload_role           = "destination"
  tags = {
    Component = "destination-network"
  }
}

module "vpc_peering" {
  source = "../../modules/vpc_peering"

  destination_route_table_ids = module.destination_vpc.private_route_table_ids
  destination_vpc_cidr        = local.network_topology.destination.vpc_cidr
  destination_vpc_id          = module.destination_vpc.vpc_id
  name                        = "${local.name_prefix}-source-to-destination"
  source_route_table_ids      = module.source_vpc.private_route_table_ids
  source_vpc_cidr             = local.network_topology.source.vpc_cidr
  source_vpc_id               = module.source_vpc.vpc_id
  tags = {
    Component = "vpc-peering"
  }
}

module "destination_workload" {
  source = "../../modules/test_workload"

  ami_id           = data.aws_ami.amazon_linux_2023.id
  destination_port = local.healthy_path.destination_port
  name             = "${local.name_prefix}-destination"
  peer_vpc_cidr    = local.network_topology.source.vpc_cidr
  role             = "destination"
  subnet_id        = module.destination_vpc.private_subnet_ids[0]
  user_data = templatefile("${path.module}/../../modules/test_workload/templates/destination.sh.tftpl", {
    destination_port = local.healthy_path.destination_port
  })
  vpc_id = module.destination_vpc.vpc_id
  tags = {
    Component = "test-workload"
  }
}

module "source_workload" {
  source = "../../modules/test_workload"

  ami_id           = data.aws_ami.amazon_linux_2023.id
  destination_port = local.healthy_path.destination_port
  name             = "${local.name_prefix}-source"
  peer_vpc_cidr    = local.network_topology.destination.vpc_cidr
  role             = "source"
  subnet_id        = module.source_vpc.private_subnet_ids[0]
  user_data = templatefile("${path.module}/../../modules/test_workload/templates/source.sh.tftpl", {
    destination_ip   = module.destination_workload.private_ip
    destination_port = local.healthy_path.destination_port
  })
  vpc_id = module.source_vpc.vpc_id
  tags = {
    Component = "test-workload"
  }

  depends_on = [module.vpc_peering]
}

resource "aws_ec2_network_insights_path" "source_to_destination_https" {
  destination      = module.destination_workload.network_interface_id
  destination_port = local.healthy_path.destination_port
  protocol         = local.healthy_path.protocol
  source           = module.source_workload.network_interface_id

  tags = {
    Component = "deterministic-diagnostics"
    Name      = "${local.name_prefix}-source-to-destination-https"
  }
}
