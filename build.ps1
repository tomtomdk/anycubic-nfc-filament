param(
    [switch]$Installer
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }
& $python -m PyInstaller --clean --noconfirm SpoolTagStudio.spec

if ($Installer) {
    $compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if (-not $compiler) {
        $compilerPaths = @(
            (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
            (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe")
        )
        $compiler = $compilerPaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    }
    if (-not $compiler) {
        throw "Inno Setup 6 is required to build the installer. The portable EXE is already in dist."
    }
    $compilerPath = if ($compiler.Source) { $compiler.Source } else { $compiler }
    & $compilerPath "installer\SpoolTagStudio.iss"
}
