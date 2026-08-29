resource "aws_security_group" "this" {
  name                   = var.name
  description            = "Phase 4 ${var.role} TCP/443 test endpoint"
  revoke_rules_on_delete = true
  vpc_id                 = var.vpc_id

  tags = merge(var.tags, {
    Name         = var.name
    WorkloadRole = var.role
  })
}

resource "aws_vpc_security_group_ingress_rule" "destination_https" {
  count = var.role == "destination" ? 1 : 0

  cidr_ipv4         = var.peer_vpc_cidr
  description       = "HTTPS from the approved Source VPC"
  from_port         = var.destination_port
  ip_protocol       = "tcp"
  security_group_id = aws_security_group.this.id
  to_port           = var.destination_port

  tags = var.tags
}

resource "aws_vpc_security_group_egress_rule" "source_https" {
  count = var.role == "source" ? 1 : 0

  cidr_ipv4         = var.peer_vpc_cidr
  description       = "HTTPS to the approved Destination VPC"
  from_port         = var.destination_port
  ip_protocol       = "tcp"
  security_group_id = aws_security_group.this.id
  to_port           = var.destination_port

  tags = var.tags
}

resource "aws_instance" "this" {
  # checkov:skip=CKV_AWS_126: Detailed monitoring adds cost without improving this short-lived network-path endpoint.
  # checkov:skip=CKV2_AWS_41: No instance role is the least-privilege choice because bootstrap and probes call no AWS APIs.
  ami                         = var.ami_id
  associate_public_ip_address = false
  ebs_optimized               = true
  instance_type               = var.instance_type
  monitoring                  = false
  subnet_id                   = var.subnet_id
  user_data                   = var.user_data
  user_data_replace_on_change = true
  vpc_security_group_ids      = [aws_security_group.this.id]
  volume_tags = merge(var.tags, {
    Name         = "${var.name}-root"
    WorkloadRole = var.role
  })

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    delete_on_termination = true
    encrypted             = true
    volume_size           = 8
    volume_type           = "gp3"
  }

  tags = merge(var.tags, {
    Name         = var.name
    WorkloadRole = var.role
  })
}
