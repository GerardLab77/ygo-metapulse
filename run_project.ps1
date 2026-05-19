$ErrorActionPreference = "Stop"

function Get-BasePython {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand -and $pythonCommand.Source -notlike "*WindowsApps*") {
        return $pythonCommand.Source
    }

    $pyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCommand) {
        $resolved = & py -3 -c "import sys; print(sys.executable)"
        if ($LASTEXITCODE -eq 0 -and $resolved) {
            return $resolved.Trim()
        }
    }

    $codexPython = "C:\Users\Student\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if (Test-Path -LiteralPath $codexPython) {
        return $codexPython
    }

    throw "No usable Python interpreter was found. Install Python 3.11+ or run this project inside Codex."
}

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$venvPython = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    $basePython = Get-BasePython
    Write-Host "Creating virtual environment with $basePython"
    & $basePython -m venv .venv
}

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Virtual environment creation failed. Expected interpreter at $venvPython"
}

Write-Host "Installing dependencies"
& $venvPython -m pip install -r requirements.txt

Write-Host "Running ingestion"
& $venvPython -m src.ingest

Write-Host "Starting Streamlit"
& $venvPython -m streamlit run app.py
