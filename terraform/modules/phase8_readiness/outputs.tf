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

output "approval_lambda_function_name" {
  description = "Approval Lambda function name."
  value       = aws_lambda_function.approval.function_name
}

output "approval_lambda_function_arn" {
  description = "Approval Lambda function ARN."
  value       = aws_lambda_function.approval.arn
}

output "approval_lambda_log_group_name" {
  description = "Approval Lambda CloudWatch log group name."
  value       = aws_cloudwatch_log_group.approval.name
}

output "approval_lambda_log_group_arn" {
  description = "Approval Lambda CloudWatch log group ARN."
  value       = aws_cloudwatch_log_group.approval.arn
}

output "remediation_lambda_function_name" {
  description = "Remediation Lambda function name."
  value       = aws_lambda_function.remediation.function_name
}

output "remediation_lambda_function_arn" {
  description = "Remediation Lambda function ARN."
  value       = aws_lambda_function.remediation.arn
}

output "remediation_lambda_log_group_name" {
  description = "Remediation Lambda CloudWatch log group name."
  value       = aws_cloudwatch_log_group.remediation.name
}

output "remediation_lambda_log_group_arn" {
  description = "Remediation Lambda CloudWatch log group ARN."
  value       = aws_cloudwatch_log_group.remediation.arn
}
