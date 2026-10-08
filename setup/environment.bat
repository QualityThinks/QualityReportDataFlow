@echo off
setlocal EnableExtensions DisableDelayedExpansion
title Developer Workstation Setup

:: Request administrator rights. This is needed to clone directly under C:\.
net session >nul 2>&1
if not "%errorlevel%"=="0" (
    echo Requesting administrator permission...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

set "LOG_FILE=%TEMP%\developer-setup.log"
echo Setup started at %DATE% %TIME% > "%LOG_FILE%"

echo.
echo ============================================================
echo   Developer Workstation Setup
echo ============================================================
echo.

:: Confirm that Windows Package Manager is available.
where winget.exe >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Windows Package Manager ^(winget^) was not found.
    echo Install or update "App Installer" from Microsoft Store, then rerun.
    goto :failed
)

call :InstallPackage "Python 3.13" "Python.Python.3.13"
if errorlevel 1 goto :failed

call :InstallPackage "Git" "Git.Git"
if errorlevel 1 goto :failed

call :InstallPackage "Notepad++" "Notepad++.Notepad++"
if errorlevel 1 goto :failed

:: Find Python and explicitly add its installation and Scripts folders
:: to the current user's persistent PATH without overwriting existing entries.
set "PYTHON_EXE="
for /f "usebackq delims=" %%P in (`py -3.13 -c "import sys; print(sys.executable)" 2^>nul`) do set "PYTHON_EXE=%%P"

if not defined PYTHON_EXE (
    echo [ERROR] Python 3.13 was installed, but its executable could not be located.
    goto :failed
)

for %%P in ("%PYTHON_EXE%") do set "PYTHON_DIR=%%~dpP"
if "%PYTHON_DIR:~-1%"=="\" set "PYTHON_DIR=%PYTHON_DIR:~0,-1%"
set "PYTHON_SCRIPTS=%PYTHON_DIR%\Scripts"

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command ^
  "$items = @('%PYTHON_DIR%', '%PYTHON_SCRIPTS%');" ^
  "$path = [Environment]::GetEnvironmentVariable('Path','User');" ^
  "$parts = @($path -split ';' | Where-Object { $_ });" ^
  "foreach ($item in $items) { if ($parts -notcontains $item) { $parts += $item } };" ^
  "[Environment]::SetEnvironmentVariable('Path', ($parts -join ';'), 'User')"
if errorlevel 1 (
    echo [ERROR] Could not update the user PATH.
    goto :failed
)

:: Make Python and Git available to the rest of this batch immediately.
set "PATH=%PYTHON_DIR%;%PYTHON_SCRIPTS%;%ProgramFiles%\Git\cmd;%PATH%"

echo [OK] Python folders were added to the user PATH.

:: Verify installations.
echo.
echo Verifying installed tools...
py -3.13 --version || goto :failed
git --version || goto :failed

:: Accept the repository URL as the first argument, or ask when run normally.
set "REPOSITORY_URL=%~1"
if not defined REPOSITORY_URL (
    echo.
    set /p "REPOSITORY_URL=Enter the Git repository URL: "
)

if not defined REPOSITORY_URL (
    echo [ERROR] No repository URL was provided.
    goto :failed
)

:: Basic URL safety/format check. Git performs the authoritative validation.
echo(%REPOSITORY_URL%| findstr /r /i "^https:// ^http:// ^ssh:// ^git@" >nul
if errorlevel 1 (
    echo [ERROR] The repository URL must begin with https://, http://, ssh://, or git@.
    goto :failed
)

echo.
echo Cloning repository into C:\ ...
pushd C:\
git clone "%REPOSITORY_URL%"
set "CLONE_RESULT=%errorlevel%"
popd

if not "%CLONE_RESULT%"=="0" (
    echo [ERROR] Git clone failed. Check the URL, credentials, network, and destination folder.
    goto :failed
)

echo.
echo ============================================================
echo   Setup completed successfully.
echo ============================================================
echo Open a new Command Prompt or PowerShell window to use the updated PATH.
echo Log: %LOG_FILE%
echo.
pause
exit /b 0

:InstallPackage
set "DISPLAY_NAME=%~1"
set "PACKAGE_ID=%~2"
echo.
echo Installing or updating %DISPLAY_NAME%...
winget.exe install --id "%PACKAGE_ID%" --exact --silent --accept-package-agreements --accept-source-agreements --disable-interactivity >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo [ERROR] Failed to install %DISPLAY_NAME%. See: %LOG_FILE%
    exit /b 1
)
echo [OK] %DISPLAY_NAME%
exit /b 0

:failed
echo.
echo ============================================================
echo   Setup did not complete.
echo ============================================================
echo Review the messages above and the log file:
echo %LOG_FILE%
echo.
pause
exit /b 1
