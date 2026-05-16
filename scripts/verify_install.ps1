# verify_install.ps1
# Verifica que a maquina atende os requisitos para rodar o ZapManager Pro.
# Uso: powershell -ExecutionPolicy Bypass -File verify_install.ps1

$ErrorActionPreference = "Continue"
Write-Host "=== Verificacao de pre-requisitos ZapManager Pro ===" -ForegroundColor Cyan
Write-Host ""

$problems = 0

function Check($label, $ok, $detail) {
    if ($ok) {
        Write-Host "[OK]    $label" -ForegroundColor Green
        if ($detail) { Write-Host "        $detail" -ForegroundColor DarkGray }
    } else {
        Write-Host "[FALHA] $label" -ForegroundColor Red
        if ($detail) { Write-Host "        $detail" -ForegroundColor Yellow }
        $script:problems += 1
    }
}

# 1. Windows version
$os = Get-CimInstance Win32_OperatingSystem
$winOk = [int]$os.BuildNumber -ge 17763   # Windows 10 1809 ou superior
Check "Windows 10/11" $winOk "Detectado: $($os.Caption) build $($os.BuildNumber)"

# 2. Browser (Edge ou Chrome)
$browserPaths = @(
    "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "C:\Program Files\Google\Chrome\Application\chrome.exe",
    "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)
$browser = $browserPaths | Where-Object { Test-Path $_ } | Select-Object -First 1
# A partir da v4.2.4 o instalador embute Chromium proprio em resources/chromium.
# Browser do sistema vira opcional (so e usado como fallback se a deteccao do bundle falhar).
if ($null -ne $browser) {
    Check "Browser do sistema (opcional, usado como fallback)" $true "Encontrado: $browser"
} else {
    Write-Host "[INFO]  Sem browser do sistema. Sera usado o Chromium embutido (v4.2.4+)." -ForegroundColor Cyan
}

# 3. Espaco em disco no LocalAppData (precisa de ~500MB para instalar com Chromium embutido)
$drive = (Get-Item $env:LOCALAPPDATA).PSDrive
$freeMB = [math]::Round($drive.Free / 1MB)
Check "Espaco em disco no LocalAppData >= 800MB" ($freeMB -ge 800) "$freeMB MB livres em $($drive.Name):"

# 4. Permissao de escrita em LocalAppData
$testPath = Join-Path $env:LOCALAPPDATA "zap_write_test_$([guid]::NewGuid()).tmp"
try {
    "test" | Out-File -FilePath $testPath -ErrorAction Stop
    Remove-Item $testPath -ErrorAction SilentlyContinue
    Check "Permissao de escrita em LocalAppData" $true ""
} catch {
    Check "Permissao de escrita em LocalAppData" $false $_.Exception.Message
}

# 5. Portas 5050 e 3001 livres
$port5050 = Get-NetTCPConnection -State Listen -LocalPort 5050 -ErrorAction SilentlyContinue
$port3001 = Get-NetTCPConnection -State Listen -LocalPort 3001 -ErrorAction SilentlyContinue
Check "Porta 5050 livre" ($null -eq $port5050) ($(if ($port5050) { "Em uso por PID $($port5050.OwningProcess)" } else { "" }))
Check "Porta 3001 livre" ($null -eq $port3001) ($(if ($port3001) { "Em uso por PID $($port3001.OwningProcess)" } else { "" }))

# 6. .NET Framework 4.5+ (necessario pro instalador NSIS)
$net = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full" -Name Release -ErrorAction SilentlyContinue
$netOk = $net -and $net.Release -ge 378389
Check ".NET Framework 4.5+ instalado" $netOk $(if ($net) { "Release: $($net.Release)" } else { "nao detectado" })

Write-Host ""
if ($problems -eq 0) {
    Write-Host "=== Pre-requisitos OK. Pode instalar. ===" -ForegroundColor Green
    exit 0
} else {
    Write-Host "=== $problems problema(s) encontrado(s). Resolva antes de instalar. ===" -ForegroundColor Red
    exit 1
}
