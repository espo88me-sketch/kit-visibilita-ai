@echo off
REM Doppio clic per avviare il kit su Windows.
cd /d "%~dp0"
chcp 65001 >nul
where python >nul 2>nul
if errorlevel 1 (
  where py >nul 2>nul
  if errorlevel 1 (
    echo Python non e' installato. Scaricalo da https://www.python.org/downloads/ ^(spunta "Add python.exe to PATH"^) e riprova.
    pause
    exit /b 1
  )
  py -3 avvia.py %*
) else (
  python avvia.py %*
)
echo.
pause
