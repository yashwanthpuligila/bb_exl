@echo off
echo.
echo ========================================
echo   Order Management - File Access Fix
echo ========================================
echo.
echo It looks like Excel has the orders.xlsx file open.
echo.
echo To fix this issue:
echo.
echo 1. Close Microsoft Excel completely
echo 2. Wait a few seconds
echo 3. Try running the GUI again
echo.
echo Alternative solutions:
echo.
echo - Check if any Excel processes are running in Task Manager
echo - Make sure you have write permissions to this folder
echo - Try running as Administrator if needed
echo.
echo Press any key when Excel is closed, then try the GUI again...
pause
echo.
echo Starting Order Management GUI...
python order_gui.py