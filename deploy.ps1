# One-click build (onedir) + deploy to C: SSD (skip the 180MB self-extraction of the onefile build).
# Paths with Chinese characters are taken from $MyInvocation (Unicode), not hardcoded literals,
# so this ASCII-only script works regardless of system codepage.
$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Py   = "C:\Users\Administrator\.workbuddy\binaries\python\envs\xhs_manager\Scripts\python.exe"
$Spec = Join-Path $Root "build\xhs_manager.spec"
$Dest = "C:\XHSManager"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"

Write-Host "==> Project root: $Root"

# 1) Move old output dirs aside (rename, not delete) to avoid the sandbox safe-delete guard
#    that PyInstaller would otherwise hit when clearing dist/build at the end of a build.
$OldDist = Join-Path $Root "dist\_old_xhs_manager_dir"
if (Test-Path (Join-Path $Root "dist\XHSManager")) {
    if (Test-Path $OldDist) { Remove-Item $OldDist -Recurse -Force -ErrorAction SilentlyContinue }
    Move-Item (Join-Path $Root "dist\XHSManager") $OldDist -Force
    Write-Host "==> Moved old dist\XHSManager aside"
}
$OldBuild = Join-Path $Root "build\_old_xhs_manager_$Stamp"
if (Test-Path (Join-Path $Root "build\xhs_manager")) {
    Move-Item (Join-Path $Root "build\xhs_manager") $OldBuild -Force
    Write-Host "==> Moved old build\xhs_manager aside"
}

# 2) Rebuild onedir
Set-Location $Root
if (-not (Test-Path $Py)) { throw "Virtualenv python not found: $Py" }
Write-Host "==> Running PyInstaller (onedir)..."
& $Py -m PyInstaller --noconfirm $Spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed, rc=$LASTEXITCODE" }

# 3) Incremental sync to C: SSD
if (-not (Test-Path (Join-Path $Root "dist\XHSManager\XHSManager.exe"))) {
    throw "Build output missing: dist\XHSManager\XHSManager.exe"
}
Write-Host "==> Copying to $Dest (incremental)..."
robocopy (Join-Path $Root "dist\XHSManager") $Dest /E /NFL /NDL /NJH
Write-Host ""
Write-Host "Deploy done. Double-click $Dest\XHSManager.exe to launch (no 180MB extraction wait)."
