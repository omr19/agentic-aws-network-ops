# Test Workload Module

Creates one short-lived, IMDSv2-only, encrypted-root EC2 endpoint and a role-specific
security group. The destination serves a self-signed HTTPS response using software
already present in Amazon Linux 2023; the source continuously probes that private IP.
Neither endpoint has a public IP, broad security-group rule, IAM role, or internet-egress
dependency. Their primary ENIs support deterministic Reachability Analyzer checks.
