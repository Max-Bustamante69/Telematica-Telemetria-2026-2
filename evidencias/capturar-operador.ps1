# Evidencia individual (Windows): consulta al servidor en la nube como operador.
#   pwsh -File evidencias\capturar-operador.ps1
Set-Location (Split-Path $PSScriptRoot -Parent)
whoami
hostname
Get-Date
nslookup telemetria.digitdeck.co
python operator_client\operator_client.py --server telemetria.digitdeck.co --cmd LIST_NODES
python operator_client\operator_client.py --server telemetria.digitdeck.co --cmd GET_ALERTS
python operator_client\operator_client.py --server telemetria.digitdeck.co --cmd SYSTEM_STATUS
