@echo off
setlocal enabledelayedexpansion
echo ============================================================
echo   Creating Desktop Shortcut for Sri Laxmi Gayatri ERP...
echo ============================================================
echo.

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "ICON_PATH=%SCRIPT_DIR%\web\icons\app_icon.ico"
set "APP_SCRIPT=%SCRIPT_DIR%\desktop_app.py"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$scriptDir = '%SCRIPT_DIR%';" ^
  "$iconPath = '%ICON_PATH%';" ^
  "$appScript = '%APP_SCRIPT%';" ^
  "$ws = New-Object -ComObject WScript.Shell;" ^
  "$desktop = [Environment]::GetFolderPath('Desktop');" ^
  "$shortcutPath = Join-Path $desktop 'Invoice ERP.lnk';" ^
  "$pyw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source;" ^
  "if (-not $pyw -or -not (Test-Path $pyw)) { $py = (Get-Command python.exe -ErrorAction SilentlyContinue).Source; if ($py) { $dir = Split-Path $py; $cand = Join-Path $dir 'pythonw.exe'; if (Test-Path $cand) { $pyw = $cand } else { $pyw = $py } } };" ^
  "if (-not $pyw) { $pyw = 'pythonw.exe' };" ^
  "$s = $ws.CreateShortcut($shortcutPath);" ^
  "$s.TargetPath = $pyw;" ^
  "$s.Arguments = '\"' + $appScript + '\"';" ^
  "$s.WorkingDirectory = $scriptDir;" ^
  "if (Test-Path $iconPath) { $s.IconLocation = $iconPath };" ^
  "$s.Description = 'Sri Laxmi Gayatri Traders - Invoice ERP';" ^
  "$s.Save();" ^
  "Write-Output \"Shortcut target: $pyw\";" ^
  "Write-Output \"Shortcut created: $shortcutPath\";"

echo.
echo ============================================================
echo   [OK] Desktop shortcut 'Invoice ERP' created successfully!
echo   Target: %APP_SCRIPT%
echo ============================================================
echo.
pause
