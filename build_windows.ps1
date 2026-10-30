$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $projectRoot "dist\Sudoku.exe"
$tickerPath = Join-Path $projectRoot "dist\ticker_messages.txt"
$zipPath = Join-Path $projectRoot "dist\Sudoku-Windows.zip"

Push-Location $projectRoot
try {
    python -m pip install -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install build requirements."
    }

    python -m PyInstaller `
        --noconfirm `
        --clean `
        --onefile `
        --windowed `
        --name Sudoku `
        --add-data "$projectRoot\Sprite-0001.svg;." `
        --distpath (Join-Path $projectRoot "dist") `
        --workpath (Join-Path $projectRoot "build") `
        --specpath (Join-Path $projectRoot "build") `
        sudoku_ui.py
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed to build the game."
    }

    Copy-Item -LiteralPath (Join-Path $projectRoot "ticker_messages.txt") `
        -Destination $tickerPath -Force
    Compress-Archive -LiteralPath @($exePath, $tickerPath) `
        -DestinationPath $zipPath -Force

    Write-Host "Build complete: $zipPath"
    Write-Host "Distribute the ZIP and tell players to extract it before launching Sudoku.exe."
}
finally {
    Pop-Location
}
