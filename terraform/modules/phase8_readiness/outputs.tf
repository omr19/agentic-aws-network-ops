output "approval_table_name" {
  description = "Dedicated on-demand approval table name."
  value       = aws_dynamodb_table.approvals.name
}

output "approval_table_arn" {
  description = "Dedicated approval table ARN."
  value       = aws_dynamodb_table.approvals.arn
}

output "approval_lambda_role_arn" {
  description = "Separate Approval Lambda execution role ARN."
  value       = aws_iam_role.approval_lambda.arn
}

output "remediation_lambda_role_arn" {
  description = "Separate remediation Lambda execution role ARN."
  value       = aws_iam_role.remediation_lambda.arn
}
