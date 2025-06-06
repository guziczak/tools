@echo off

REM Check for admin rights
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running as Administrator - Good!
) else (
    echo This script needs Administrator privileges.
    echo Restarting as Administrator...
    powershell -Command "Start-Process '%0' -Verb RunAs"
    exit /b
)

echo ====================================
echo CLEAN Python Installer
echo ====================================
echo This will REMOVE all existing Python and install fresh
echo.

set /p confirm=Continue? This will delete existing Python installations! (y/N):
if /i not "%confirm%"=="y" (
    echo Cancelled.
    pause
    exit /b 0
)

echo.
echo ========================================
echo STEP 1: Removing existing Python
echo ========================================

REM Stop any Python processes
echo Stopping Python processes...
taskkill /F /IM python.exe >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1

REM Remove old portable Python from C:\Python312
if exist "C:\Python312" (
    echo Removing old Python from C:\Python312...
    rmdir /S /Q "C:\Python312" >nul 2>&1
    if exist "C:\Python312" (
        echo Warning: Could not fully remove C:\Python312
        echo Some files may be in use
    ) else (
        echo Successfully removed C:\Python312
    )
)

REM Remove Python from PATH completely
echo Cleaning PATH environment...

REM Get current system PATH
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SystemPath=%%b"

REM Remove all Python entries from system PATH
set "CleanSystemPath=%SystemPath%"
set "CleanSystemPath=%CleanSystemPath:;C:\Python312\Scripts=%"
set "CleanSystemPath=%CleanSystemPath:;C:\Python312=%"
set "CleanSystemPath=%CleanSystemPath:C:\Python312\Scripts;=%"
set "CleanSystemPath=%CleanSystemPath:C:\Python312;=%"
set "CleanSystemPath=%CleanSystemPath:;C:\Program Files\Python312\Scripts=%"
set "CleanSystemPath=%CleanSystemPath:;C:\Program Files\Python312=%"
set "CleanSystemPath=%CleanSystemPath:C:\Program Files\Python312\Scripts;=%"
set "CleanSystemPath=%CleanSystemPath:C:\Program Files\Python312;=%"

if not "%SystemPath%"=="%CleanSystemPath%" (
    echo Updating system PATH...
    setx PATH "%CleanSystemPath%" /M >nul
)

REM Get current user PATH
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "UserPath=%%b"

REM Remove all Python entries from user PATH
set "CleanUserPath=%UserPath%"
set "CleanUserPath=%CleanUserPath:;C:\Python312\Scripts=%"
set "CleanUserPath=%CleanUserPath:;C:\Python312=%"
set "CleanUserPath=%CleanUserPath:C:\Python312\Scripts;=%"
set "CleanUserPath=%CleanUserPath:C:\Python312;=%"
set "CleanUserPath=%CleanUserPath:;C:\Program Files\Python312\Scripts=%"
set "CleanUserPath=%CleanUserPath:;C:\Program Files\Python312=%"
set "CleanUserPath=%CleanUserPath:C:\Program Files\Python312\Scripts;=%"
set "CleanUserPath=%CleanUserPath:C:\Program Files\Python312;=%"

if not "%UserPath%"=="%CleanUserPath%" (
    echo Updating user PATH...
    setx PATH "%CleanUserPath%" >nul
)

REM Clear registry entries
echo Clearing Python registry entries...
reg delete "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\python.exe" /f >nul 2>&1
reg delete "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\python3.exe" /f >nul 2>&1

REM Remove Windows Store aliases
echo Removing Windows Store Python aliases...
if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" (
    takeown /f "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" >nul 2>&1
    icacls "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" /grant "%USERNAME%:F" >nul 2>&1
    del /f /q "%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe" >nul 2>&1
)

if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe" (
    takeown /f "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe" >nul 2>&1
    icacls "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe" /grant "%USERNAME%:F" >nul 2>&1
    del /f /q "%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe" >nul 2>&1
)

powershell -Command "& {$aliases = @('python.exe', 'python3.exe'); foreach($alias in $aliases) { $path = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps' $alias; if(Test-Path $path) { Remove-Item $path -Force -ErrorAction SilentlyContinue } } }" >nul 2>&1

echo Python cleanup completed.

echo.
echo ========================================
echo STEP 2: Installing fresh Python
echo ========================================

REM Fix Windows Installer Service
echo Fixing Windows Installer Service...
net stop msiserver >nul 2>&1
net start msiserver >nul 2>&1
sc config msiserver start= demand >nul 2>&1

set PYTHON_URL=https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe
set PYTHON_INSTALLER=python-installer-clean.exe

echo Downloading fresh Python 3.12.10 installer...
curl -L -o "%PYTHON_INSTALLER%" "%PYTHON_URL%"

if not exist "%PYTHON_INSTALLER%" (
    echo Download failed! Please check your internet connection.
    pause
    exit /b 1
)

echo.
echo Installing Python to C:\Program Files\Python312...
echo This will install STANDARD Python (not portable/embedded)
echo.

REM Force installation to Program Files (standard location)
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=1 PrependPath=1 Include_launcher=1 Include_test=0 DefaultAllUsersTargetDir="C:\Program Files\Python312"

echo Waiting for installation to complete...
timeout /t 45 /nobreak >nul

REM Check installation
if exist "C:\Program Files\Python312\python.exe" (
    echo SUCCESS: Python installed in C:\Program Files\Python312
    set PYTHON_PATH=C:\Program Files\Python312
    goto CONFIGURE_PYTHON
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    echo Found Python in %LOCALAPPDATA%\Programs\Python\Python312
    set PYTHON_PATH=%LOCALAPPDATA%\Programs\Python\Python312
    goto CONFIGURE_PYTHON
)

echo Standard installer failed. Trying alternative methods...
del "%PYTHON_INSTALLER%" >nul 2>&1

echo.
echo ========================================
echo FALLBACK: Installing via Chocolatey
echo ========================================

REM Check if Chocolatey exists
where choco >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Chocolatey package manager...
    powershell -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command "Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"

    REM Add Chocolatey to PATH for current session
    set "PATH=%ALLUSERSPROFILE%\chocolatey\bin;%PATH%"
    call refreshenv.cmd 2>nul
)

where choco >nul 2>&1
if %errorlevel% == 0 (
    echo Installing Python via Chocolatey...
    choco install python312 -y --force --no-progress

    REM Wait for installation
    timeout /t 30 /nobreak >nul
    call refreshenv.cmd 2>nul

    REM Check if Chocolatey installation worked
    if exist "C:\Python312\python.exe" (
        echo SUCCESS: Python installed via Chocolatey to C:\Python312
        set PYTHON_PATH=C:\Python312
        goto CONFIGURE_PYTHON
    )
    if exist "C:\Program Files\Python312\python.exe" (
        echo SUCCESS: Python installed via Chocolatey to C:\Program Files\Python312
        set PYTHON_PATH=C:\Program Files\Python312
        goto CONFIGURE_PYTHON
    )
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        echo SUCCESS: Python installed via Chocolatey
        set PYTHON_PATH=%LOCALAPPDATA%\Programs\Python\Python312
        goto CONFIGURE_PYTHON
    )

    REM Search for any Python installation
    for /d %%D in ("C:\Python*") do (
        if exist "%%D\python.exe" (
            echo Found Python via Chocolatey in %%D
            set PYTHON_PATH=%%D
            goto CONFIGURE_PYTHON
        )
    )
)

echo.
echo ========================================
echo FALLBACK: Installing via WinGet
echo ========================================

where winget >nul 2>&1
if %errorlevel% == 0 (
    echo Installing Python via WinGet...
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements --scope machine

    REM Wait for installation
    timeout /t 45 /nobreak >nul

    REM Check if WinGet installation worked
    if exist "C:\Program Files\Python312\python.exe" (
        echo SUCCESS: Python installed via WinGet
        set PYTHON_PATH=C:\Program Files\Python312
        goto CONFIGURE_PYTHON
    )
    if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
        echo SUCCESS: Python installed via WinGet
        set PYTHON_PATH=%LOCALAPPDATA%\Programs\Python\Python312
        goto CONFIGURE_PYTHON
    )
    if exist "C:\Python312\python.exe" (
        echo SUCCESS: Python installed via WinGet
        set PYTHON_PATH=C:\Python312
        goto CONFIGURE_PYTHON
    )

    REM Search for any Python installation
    for /d %%D in ("C:\Program Files\Python*") do (
        if exist "%%D\python.exe" (
            echo Found Python via WinGet in %%D
            set PYTHON_PATH=%%D
            goto CONFIGURE_PYTHON
        )
    )
) else (
    echo WinGet not available
)

echo.
echo ==========================================
echo ALL INSTALLATION METHODS FAILED!
echo ==========================================
echo.
echo This system has serious issues with Python installation.
echo Possible causes:
echo 1. Antivirus blocking all installations
echo 2. Group Policy restrictions
echo 3. Corrupted Windows components
echo 4. System administrator restrictions
echo.
echo Manual solutions:
echo 1. Temporarily disable ALL antivirus software
echo 2. Check Windows Event Viewer for errors
echo 3. Run as different user with admin rights
echo 4. Download Python manually from python.org and install with GUI
echo 5. Contact system administrator
echo.
pause
exit /b 1

:CONFIGURE_PYTHON

:CONFIGURE_PYTHON
echo.
echo ========================================
echo STEP 3: Configuring fresh installation
echo ========================================

echo Configuring PATH for: %PYTHON_PATH%

REM Add Python to system PATH
for /f "tokens=2*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "CurrentSystemPath=%%b"
setx PATH "%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%CurrentSystemPath%" /M >nul
echo Updated system PATH

REM Add Python to user PATH
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "CurrentUserPath=%%b"
setx PATH "%PYTHON_PATH%;%PYTHON_PATH%\Scripts;%CurrentUserPath%" >nul
echo Updated user PATH

REM Set proper registry entries
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\python.exe" /ve /t REG_SZ /d "%PYTHON_PATH%\python.exe" /f >nul
reg add "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\python3.exe" /ve /t REG_SZ /d "%PYTHON_PATH%\python.exe" /f >nul
echo Updated registry entries

echo.
echo Testing fresh Python installation...
"%PYTHON_PATH%\python.exe" --version
if %errorlevel% == 0 (
    echo SUCCESS: Python is working!
    echo.
    echo Checking Python configuration...
    "%PYTHON_PATH%\python.exe" -c "import sys; print('Python type:', 'Standard' if hasattr(sys, 'base_prefix') else 'Unknown'); print('Isolated mode:', sys.flags.isolated); print('Environment mode:', sys.flags.ignore_environment)"
) else (
    echo ERROR: Python test failed!
)

echo.
echo Testing pip...
"%PYTHON_PATH%\python.exe" -m pip --version >nul 2>&1
if %errorlevel% == 0 (
    echo SUCCESS: pip is working!
) else (
    echo Installing pip...
    "%PYTHON_PATH%\python.exe" -m ensurepip --upgrade
)

echo.
echo ====================================
echo Fresh Installation Complete!
echo ====================================
echo.
echo Python installed at: %PYTHON_PATH%
echo Python version:
"%PYTHON_PATH%\python.exe" --version
echo.
echo CRITICAL: You MUST restart your computer or at least:
echo 1. Close ALL terminal windows (including this one)
echo 2. Wait 10 seconds
echo 3. Open a NEW Command Prompt
echo 4. Test: python --version
echo.
echo The fresh Python should show:
echo - isolated = 0 (normal mode)
echo - environment = 1 (reads environment variables)
echo.
pause