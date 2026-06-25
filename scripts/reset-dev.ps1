# scripts/reset-dev.ps1
#
# Libera los puertos de desarrollo (4200 Angular, 8000 Django) matando
# cualquier proceso que los este ocupando. Util cuando `npm start` o
# `runserver` fallan con "Port already in use" porque un proceso
# anterior quedo zombie.
#
# Uso:
#   powershell -ExecutionPolicy Bypass -File scripts\reset-dev.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\reset-dev.ps1 -DryRun
#
# Por que solo por puerto y no por nombre/cmdline:
#   El auto-reloader de Django y el wrapper de npm crean arboles de
#   procesos donde el padre (venv/npm) y el child (sys python /
#   node ng.js) tienen command-lines distintos. Filtrar por
#   "ng serve" o "runserver" puede fallar en el child que es quien
#   efectivamente bindea el puerto. Ir directo al puerto matchea siempre.

[CmdletBinding()]
param(
    [switch]$DryRun,
    [int[]]$Ports = @(4200, 8000)
)

$ErrorActionPreference = 'Continue'

# 1. Encontrar PIDs que esten escuchando en cualquiera de los puertos.
$listeners = @(
    Get-NetTCPConnection -LocalPort $Ports -State Listen -ErrorAction SilentlyContinue
)

if ($listeners.Count -eq 0) {
    Write-Host "Puertos $($Ports -join ', ') ya libres."
    exit 0
}

# Dedupe por PID -- un proceso puede escuchar en mas de un socket.
$targets = $listeners | Select-Object -ExpandProperty OwningProcess -Unique

# 2. Mostrar que se va a matar.
Write-Host "Procesos a detener:" -ForegroundColor Yellow
foreach ($pidNum in $targets) {
    $proc = Get-Process -Id $pidNum -ErrorAction SilentlyContinue
    $port = ($listeners | Where-Object OwningProcess -eq $pidNum | Select-Object -First 1).LocalPort
    if ($proc) {
        $name = $proc.ProcessName
        Write-Host ("  pid={0,-6} port={1,-5} name={2}" -f $pidNum, $port, $name)
    } else {
        Write-Host ("  pid={0,-6} port={1,-5} (no info)" -f $pidNum, $port)
    }
}

if ($DryRun) {
    Write-Host ""
    Write-Host "[DryRun] No se mata nada. Sacale -DryRun para ejecutar." -ForegroundColor Cyan
    exit 0
}

# 3. Matar. Stop-Process -Force no espera handles.
foreach ($pidNum in $targets) {
    try {
        Stop-Process -Id $pidNum -Force -ErrorAction Stop
        Write-Host ("  killed pid={0}" -f $pidNum) -ForegroundColor DarkGray
    } catch {
        Write-Host ("  ! pid {0} no pudo matarse: {1}" -f $pidNum, $_.Exception.Message) -ForegroundColor DarkYellow
    }
}

# 4. Verificacion final -- esperamos un poco para que el OS libere los sockets.
Start-Sleep -Milliseconds 400
$still = Get-NetTCPConnection -LocalPort $Ports -State Listen -ErrorAction SilentlyContinue
if ($still) {
    Write-Host ""
    Write-Host "ATENCION -- estos puertos siguen ocupados:" -ForegroundColor Red
    foreach ($conn in $still) {
        Write-Host ("  port={0} pid={1}" -f $conn.LocalPort, $conn.OwningProcess)
    }
    Write-Host "Cerra la terminal que los tiene abierto y reintenta."
    exit 1
}

Write-Host ""
Write-Host "Listo. Puertos $($Ports -join ', ') libres." -ForegroundColor Green
exit 0
