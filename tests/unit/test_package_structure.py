"""Foundation tests for the Python responsibility boundaries."""

from importlib import import_module

import pytest


@pytest.mark.parametrize(
    "module_name",
    [
        "agentic_aws_network_ops",
        "agentic_aws_network_ops.adapters",
        "agentic_aws_network_ops.agent",
        "agentic_aws_network_ops.approval",
        "agentic_aws_network_ops.diagnostics",
        "agentic_aws_network_ops.remediation",
        "agentic_aws_network_ops.shared",
    ],
)
def test_package_boundary_is_importable(module_name: str) -> None:
    """Each approved Python responsibility boundary is importable."""
    assert import_module(module_name)
