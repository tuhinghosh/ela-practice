$ErrorActionPreference = "Stop"

$imageName = "ela-mvp"
$containerName = "ela-mvp"
$dataDir = Join-Path (Get-Location) "backend/data"

New-Item -ItemType Directory -Force -Path $dataDir | Out-Null

$existing = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $containerName }
if ($existing) {
  docker rm -f $containerName | Out-Null
}

docker build -t $imageName .

if (Test-Path ".env") {
  docker run -d --name $containerName --env-file .env -p 8000:8000 -v "${dataDir}:/app/backend/data" $imageName | Out-Null
}
else {
  docker run -d --name $containerName -p 8000:8000 -v "${dataDir}:/app/backend/data" $imageName | Out-Null
}

Write-Host "ELA MVP started at http://localhost:8000"
