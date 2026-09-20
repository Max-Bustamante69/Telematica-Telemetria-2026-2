# Evidencia individual (Windows). Uso:  pwsh -File evidencias\capturar.ps1 NODE10 "Casa de Max"
# Imprime usuario, equipo y fecha, y arranca el nodo contra el servidor en la nube.
param([string]$Id = "NODE10", [string]$Location = "Casa")
Set-Location (Split-Path $PSScriptRoot -Parent)
whoami
hostname
Get-Date
python node\node.py --id $Id --server telemetria.digitdeck.co --location $Location --interval 2
