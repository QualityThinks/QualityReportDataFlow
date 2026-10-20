@echo off
setlocal EnableExtensions
title Quality Report - Python Setup

:: Installs the Python packages from requirements.txt and creates .env from
:: .env.example when it does not exist yet. Safe to run again.

:: Work from the project root, wherever this file was started from.
pushd "%~dp0.."

echo.
echo ============================================================
echo   Quality Report - Python Setup
echo ============================================================
echo.

:: Use "python" (the command the installation guide uses), else the py launcher.
set "PYTHON_CMD="
python --version >nul 2>&1 && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
    py -3 --version >nul 2>&1 && set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
    echo [ERROR] Python was not found.
    echo Install Python 3.13 with "Add python.exe to PATH" ticked, then run this file again.
    goto :failed
)

echo Using:
%PYTHON_CMD% --version

echo.
echo Installing packages from requirements.txt...
%PYTHON_CMD% -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Package installation failed. Check the internet connection and the messages above.
    goto :failed
)

%PYTHON_CMD% -c "import cryptography, dotenv, mysql.connector, numpy, openpyxl, pandas"
if errorlevel 1 (
    echo [ERROR] The packages were installed but could not be imported.
    goto :failed
)
echo [OK] Python packages

if exist ".env" (
    echo [OK] .env already exists, left unchanged
) else (
    copy /y ".env.example" ".env" >nul
    if errorlevel 1 (
        echo [ERROR] Could not create .env from .env.example.
        goto :failed
    )
    echo [OK] Created .env from .env.example
)

echo.
echo ============================================================
echo   Setup completed.
echo ============================================================
echo Next: fill in .env, see installation-module\module-en.md section 4.
echo.
popd
pause
exit /b 0

:failed
echo.
echo ============================================================
echo   Setup did not complete.
echo ============================================================
echo.
popd
pause
exit /b 1
