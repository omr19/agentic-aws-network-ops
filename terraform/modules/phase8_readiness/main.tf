resource "aws_dynamodb_table" "approvals" {
  name         = "${var.name_prefix}-phase8-approvals"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "approval_id"

  attribute {
    name = "approval_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl_epoch"
    enabled        = true
  }

  server_side_encryption {
    enabled = true
  }

  point_in_time_recovery {
    enabled = false
  }

  tags = merge(var.tags, { Component = "phase8-approval" })
}

resource "aws_iam_role" "approval_lambda" {
  name = "${var.name_prefix}-phase8-approval-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = merge(var.tags, { Component = "phase8-approval" })
}

resource "aws_iam_role" "remediation_lambda" {
  name = "${var.name_prefix}-phase8-remediation-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })

  tags = merge(var.tags, { Component = "phase8-remediation" })
}

resource "aws_iam_role_policy" "approval_persistence" {
  name = "${var.name_prefix}-phase8-approval-persistence"
  role = aws_iam_role.approval_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ApprovalTableWrite"
      Effect   = "Allow"
      Action   = ["dynamodb:PutItem", "dynamodb:GetItem"]
      Resource = aws_dynamodb_table.approvals.arn
      Condition = {
        StringEquals = { "aws:RequestedRegion" = var.region }
      }
    }]
  })
}

resource "aws_iam_role_policy" "remediation_persistence" {
  name = "${var.name_prefix}-phase8-remediation-persistence"
  role = aws_iam_role.remediation_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ApprovalTableConsumeAndRecord"
      Effect   = "Allow"
      Action   = ["dynamodb:GetItem", "dynamodb:UpdateItem"]
      Resource = aws_dynamodb_table.approvals.arn
      Condition = {
        StringEquals = { "aws:RequestedRegion" = var.region }
      }
    }]
  })
}

resource "aws_iam_role_policy" "remediation_write" {
  name = "${var.name_prefix}-phase8-remediation-write"
  role = aws_iam_role.remediation_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "RestoreSecurityGroupIngress"
        Effect   = "Allow"
        Action   = "ec2:AuthorizeSecurityGroupIngress"
        Resource = "arn:aws:ec2:${var.region}:*:security-group/${var.destination_security_group_id}"
        Condition = {
          StringEquals = {
            "aws:RequestedRegion"         = var.region
            "aws:ResourceTag/Project"     = var.tags.Project
            "aws:ResourceTag/Environment" = var.tags.Environment
            "aws:ResourceTag/ManagedBy"   = var.tags.ManagedBy
            "ec2:Vpc"                     = var.destination_vpc_id
          }
        }
      },
      {
        Sid    = "RestorePeeringRoutes"
        Effect = "Allow"
        Action = ["ec2:CreateRoute", "ec2:ReplaceRoute"]
        Resource = concat(
          [for id in var.source_route_table_ids : "arn:aws:ec2:${var.region}:*:route-table/${id}"],
          [for id in var.destination_route_table_ids : "arn:aws:ec2:${var.region}:*:route-table/${id}"]
        )
        Condition = {
          StringEquals = {
            "aws:RequestedRegion"         = var.region
            "aws:ResourceTag/Project"     = var.tags.Project
            "aws:ResourceTag/Environment" = var.tags.Environment
            "aws:ResourceTag/ManagedBy"   = var.tags.ManagedBy
          }
        }
      },
      {
        Sid      = "RestoreNetworkAclEntry"
        Effect   = "Allow"
        Action   = "ec2:ReplaceNetworkAclEntry"
        Resource = "arn:aws:ec2:${var.region}:*:network-acl/${var.destination_network_acl_id}"
        Condition = {
          StringEquals = {
            "aws:RequestedRegion"         = var.region
            "aws:ResourceTag/Project"     = var.tags.Project
            "aws:ResourceTag/Environment" = var.tags.Environment
            "aws:ResourceTag/ManagedBy"   = var.tags.ManagedBy
            "ec2:Vpc"                     = var.destination_vpc_id
          }
        }
      }
    ]
  })
}
