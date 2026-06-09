@echo off
REM Windows wrapper to execute the Python installation script
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    where python3 >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [WARN] Python 3 is not found in your PATH.
        echo Python is required to run the AI Coding Config installer.
        set /p choice="Would you like to install Python 3 now via Winget? (y/n): "
        if /i "%choice%"=="y" (
            echo Installing Python 3 via Winget...
            winget install Python.Python.3
            if %ERRORLEVEL% neq 0 (
                echo [ERROR] Failed to install Python. Please install it manually from https://python.org
                exit /b 1
            )
            echo [SUCCESS] Python installed successfully! Please restart this terminal and run install.bat again.
            exit /b 0
        ) else (
            echo [ERROR] Python 3 installation was canceled. Exiting.
            exit /b 1
        )
    ) else (
        python3 "%~dp0install.py" %*
    )
) else (
    python "%~dp0install.py" %*
)
