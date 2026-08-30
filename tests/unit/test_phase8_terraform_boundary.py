from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[2]
MODULE_MAIN = ROOT / "terraform/modules/phase8_readiness/main.tf"
MODULE_VARIABLES = ROOT / "terraform/modules/phase8_readiness/variables.tf"
MODULE_OUTPUTS = ROOT / "terraform/modules/phase8_readiness/outputs.tf"
LAB_MAIN = ROOT / "terraform/environments/lab/main.tf"
LAB_OUTPUTS = ROOT / "terraform/environments/lab/outputs.tf"


def test_phase8_declares_two_local_zip_lambda_functions_and_log_groups() -> None:
    source = MODULE_MAIN.read_text(encoding="utf-8")
    assert source.count('resource "aws_lambda_function"') == 2
    assert source.count('resource "aws_cloudwatch_log_group"') == 2
    assert source.count('resource "aws_iam_role_policy"') == 6
    assert 'resource "aws_lambda_permission"' not in source

    for component, handler in (
        ("approval", "agentic_aws_network_ops.adapters.approval_lambda.handler"),
        ("remediation", "agentic_aws_network_ops.adapters.remediation_lambda.handler"),
    ):
        assert f'resource "aws_lambda_function" "{component}"' in source
        assert f'handler          = "{handler}"' in source
        assert 'runtime          = "python3.13"' in source
        assert 'architectures    = ["arm64"]' in source
        assert "memory_size      = 256" in source
        assert "timeout          = 30" in source
        assert f"filename         = var.{component}_lambda_filename" in source
        assert f"filebase64sha256(var.{component}_lambda_filename)" in source
        assert 'retention_in_days = 7' in source
        assert "PHASE8_AWS_REGION" in source
        assert "PHASE8_APPROVAL_TABLE_NAME" in source
    assert 'PHASE8_AUTHORIZED_APPROVERS_JSON' in source
    assert 'PHASE8_DESTINATION_SECURITY_GROUP_ID' in source
    assert 'PHASE8_DESTINATION_VPC_ID' in source
    assert 'PHASE8_SOURCE_VPC_ID' in source


def test_phase8_logging_policy_is_narrow_and_agentcore_free() -> None:
    source = MODULE_MAIN.read_text(encoding="utf-8")
    assert 'Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]' in source
    assert 'logs:CreateLogGroup' not in source
    assert 'logs:DescribeLogGroups' not in source
    assert 'aws_lambda_permission' not in source
    assert "agentcore" not in source.lower()


def test_phase8_root_wires_local_artifacts_and_exposes_deployment_outputs() -> None:
    variables = MODULE_VARIABLES.read_text(encoding="utf-8")
    outputs = MODULE_OUTPUTS.read_text(encoding="utf-8")
    lab_main = LAB_MAIN.read_text(encoding="utf-8")
    lab_outputs = LAB_OUTPUTS.read_text(encoding="utf-8")

    assert 'variable "approval_lambda_filename"' in variables
    assert 'variable "remediation_lambda_filename"' in variables
    assert ".artifacts/phase8-approval-lambda/phase8-approval-lambda.zip" in lab_main
    assert ".artifacts/phase8-remediation-lambda/phase8-remediation-lambda.zip" in lab_main
    for name in (
        "approval_lambda_function_name",
        "approval_lambda_function_arn",
        "approval_lambda_log_group_name",
        "approval_lambda_log_group_arn",
        "remediation_lambda_function_name",
        "remediation_lambda_function_arn",
        "remediation_lambda_log_group_name",
        "remediation_lambda_log_group_arn",
    ):
        assert f'output "{name}"' in outputs
        assert f"module.phase8_readiness[0].{name}" in lab_outputs
