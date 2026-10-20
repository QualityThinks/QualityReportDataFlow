@echo off
setlocal EnableExtensions

:: Runs the quality report once and appends the output to report.log in the
:: project folder. Point Windows Task Scheduler at this file to send the
:: report automatically.

:: Work from the project root, wherever this file was started from.
pushd "%~dp0.."
set "PYTHONIOENCODING=utf-8"

:: Same Python as setup\python-configurations.bat installed the packages for.
set "PYTHON_CMD="
python --version >nul 2>&1 && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
    py -3 --version >nul 2>&1 && set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
    echo [%DATE% %TIME%] Python was not found.>> report.log
    echo Python was not found. See report.log.
    popd
    exit /b 1
)

echo.>> report.log
echo ===== %DATE% %TIME% =====>> report.log
%PYTHON_CMD% main.py >> report.log 2>&1
set "RESULT=%errorlevel%"

echo Report run finished with exit code %RESULT%. Output: %CD%\report.log
popd
exit /b %RESULT%
