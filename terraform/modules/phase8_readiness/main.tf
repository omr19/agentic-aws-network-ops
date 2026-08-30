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

resource "aws_iam_role_policy" "remediation_read" {
  name = "${var.name_prefix}-phase8-remediation-read"
  role = aws_iam_role.remediation_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "RemediationReadPreflightAndVerification"
      Effect = "Allow"
      Action = [
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeRouteTables",
        "ec2:DescribeNetworkAcls",
      ]
      Resource = "*"
      Condition = {
        StringEquals = { "aws:RequestedRegion" = var.region }
      }
    }]
  })
}

resource "aws_cloudwatch_log_group" "approval" {
  name              = "/aws/lambda/${var.name_prefix}-phase8-approval"
  retention_in_days = 7

  tags = merge(var.tags, { Component = "phase8-approval" })
}

resource "aws_cloudwatch_log_group" "remediation" {
  name              = "/aws/lambda/${var.name_prefix}-phase8-remediation"
  retention_in_days = 7

  tags = merge(var.tags, { Component = "phase8-remediation" })
}

resource "aws_iam_role_policy" "approval_logging" {
  name = "${var.name_prefix}-phase8-approval-logging"
  role = aws_iam_role.approval_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "ApprovalLambdaCloudWatchLogging"
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.approval.arn}:*"
      Condition = {
        StringEquals = { "aws:RequestedRegion" = var.region }
      }
    }]
  })
}

resource "aws_iam_role_policy" "remediation_logging" {
  name = "${var.name_prefix}-phase8-remediation-logging"
  role = aws_iam_role.remediation_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid      = "RemediationLambdaCloudWatchLogging"
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.remediation.arn}:*"
      Condition = {
        StringEquals = { "aws:RequestedRegion" = var.region }
      }
    }]
  })
}

resource "aws_lambda_function" "approval" {
  function_name    = "${var.name_prefix}-phase8-approval"
  filename         = var.approval_lambda_filename
  source_code_hash = filebase64sha256(var.approval_lambda_filename)
  role             = aws_iam_role.approval_lambda.arn
  handler          = "agentic_aws_network_ops.adapters.approval_lambda.handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  memory_size      = 256
  timeout          = 30

  environment {
    variables = {
      PHASE8_AWS_REGION                = var.region
      PHASE8_APPROVAL_TABLE_NAME       = aws_dynamodb_table.approvals.name
      PHASE8_AUTHORIZED_APPROVERS_JSON = jsonencode(var.authorized_approvers)
    }
  }

  tags = merge(var.tags, { Component = "phase8-approval" })

  depends_on = [aws_iam_role_policy.approval_logging]
}

resource "aws_lambda_function" "remediation" {
  function_name    = "${var.name_prefix}-phase8-remediation"
  filename         = var.remediation_lambda_filename
  source_code_hash = filebase64sha256(var.remediation_lambda_filename)
  role             = aws_iam_role.remediation_lambda.arn
  handler          = "agentic_aws_network_ops.adapters.remediation_lambda.handler"
  runtime          = "python3.13"
  architectures    = ["arm64"]
  memory_size      = 256
  timeout          = 30

  environment {
    variables = {
      PHASE8_AWS_REGION                    = var.region
      PHASE8_APPROVAL_TABLE_NAME           = aws_dynamodb_table.approvals.name
      PHASE8_DESTINATION_SECURITY_GROUP_ID = var.destination_security_group_id
      PHASE8_DESTINATION_VPC_ID            = var.destination_vpc_id
      PHASE8_SOURCE_VPC_ID                 = var.source_vpc_id
    }
  }

  tags = merge(var.tags, { Component = "phase8-remediation" })

  depends_on = [aws_iam_role_policy.remediation_logging]
}
