@echo off
setlocal enabledelayedexpansion

echo ==========================================
echo  Reconciliation Tool v2.0 - Service Uninstaller
echo ==========================================
echo.
echo This will completely remove the Reconciliation Tool Windows Service.
echo Requires Administrator privileges.
echo.

cd /d "%~dp0"

:: ---- CHECK ADMIN PRIVILEGES ----
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Administrator privileges required!
    echo Please run this batch file as Administrator.
    pause
    exit /b 1
)

set "SERVICE_NAME=ReconciliationTool"

echo [INFO] Stopping service (if running)...
net stop %SERVICE_NAME% >nul 2>&1
sc stop %SERVICE_NAME% >nul 2>&1
timeout /t 2 /nobreak >nul

echo [INFO] Deleting service...
if exist "tools\nssm.exe" (
    tools\nssm.exe remove %SERVICE_NAME% confirm >nul 2>&1
) else (
    sc delete %SERVICE_NAME% >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo.
echo ==========================================
echo  SERVICE UNINSTALLED SUCCESSFULLY
echo ==========================================
echo.
echo The background service has been completely removed from Windows.
echo If you wish to completely uninstall the tool from your computer, 
echo you can now safely delete this entire folder.
echo.
pause
endlocal
