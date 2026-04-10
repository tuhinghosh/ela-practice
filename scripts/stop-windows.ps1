$ErrorActionPreference = "Stop"

$containerName = "ela-mvp"

$existing = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $containerName }
if ($existing) {
  docker rm -f $containerName | Out-Null
  Write-Host "Stopped and removed $containerName"
}
else {
  Write-Host "Container $containerName is not running."
}
