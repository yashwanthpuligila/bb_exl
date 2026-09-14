@echo off
setlocal
echo Creating Desktop Shortcut for Invoice ERP...

set "SCRIPT_DIR=%~dp0"
set "ICON_PATH=%SCRIPT_DIR%web\icons\app_icon.ico"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; " ^
  "$desktop = [Environment]::GetFolderPath('Desktop'); " ^
  "$s = $ws.CreateShortcut(\"$desktop\Invoice ERP.lnk\"); " ^
  "$s.TargetPath = 'pythonw.exe'; " ^
  "$s.Arguments = '\"%SCRIPT_DIR%desktop_app.py\"'; " ^
  "$s.WorkingDirectory = '%SCRIPT_DIR%'; " ^
  "$s.IconLocation = '%ICON_PATH%'; " ^
  "$s.Description = 'Sri Laxmi Gayatri Traders - Invoice ERP App'; " ^
  "$s.Save()"

echo.
echo ============================================================
echo   [OK] Desktop shortcut 'Invoice ERP' created successfully!
echo   You can now launch the app directly from your Desktop.
echo ============================================================
pause
