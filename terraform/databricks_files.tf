# Container Approach - Script único consolidado
# Solução robusta para Community Edition

# Comentado - será feito upload manual
# resource "databricks_file" "linkedin_pipeline_runner" {
#   source = "${path.module}/../linkedin_pipeline_runner.py"
#   path   = "/Shared/linkedin_pipeline_runner.py"
# }

# Output path para referência
output "python_runner_path" {
  description = "Path do script consolidado no workspace (upload manual)"
  value = "/Shared/linkedin_pipeline_runner.py"
}
