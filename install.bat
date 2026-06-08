@echo off
REM Windows wrapper to execute the Python installation script
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    where python3 >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] python is not found in your PATH.
        echo Please install Python 3 and add it to your System PATH.
        exit /b 1
    ) else (
        python3 "%~dp0install.py" %*
    )
) else (
    python "%~dp0install.py" %*
)
