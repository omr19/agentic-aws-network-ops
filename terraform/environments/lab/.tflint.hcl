config {
  call_module_type = "local"
  force            = false
  plugin_dir       = ".tflint.d/plugins"
}

plugin "aws" {
  enabled = true
  source  = "github.com/terraform-linters/tflint-ruleset-aws"
  version = "0.48.0"
}
