@echo off
REM Windows wrapper to execute the bash installation script
where bash >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] bash is not found in your PATH. 
    echo Please run this script inside Git Bash, WSL, or install Git for Windows.
    exit /b 1
)
bash "%~dp0install.sh" %*
