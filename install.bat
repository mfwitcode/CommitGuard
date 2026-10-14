@echo off
REM ==============================================================================
REM CommitGuard Installer for Windows
REM ==============================================================================

setlocal enabledelayedexpansion

echo ====================================================
echo      CommitGuard - Git Pre-commit Hook Installer    
echo ====================================================
echo.

REM Check if Python is installed
where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=py
) else (
    where python >nul 2>&1
    if !ERRORLEVEL! neq 0 (
        echo [ERROR] Python is not found in your system PATH.
        echo Please install Python 3.8+ and ensure "Add Python to PATH" is checked.
        echo.
        pause
        exit /b 1
    ) else (
        set PYTHON_CMD=python
    )
)

echo Detected Python:
%PYTHON_CMD% --version
echo.

REM Check if inside a Git repository
if not exist ".git" (
    git rev-parse --is-inside-work-tree >nul 2>&1
    if !ERRORLEVEL! neq 0 (
        echo [NOTICE] Current directory is not a Git repository.
        set /p INIT_GIT="Would you like to initialize a new git repository now? (Y/N): "
        if /i "!INIT_GIT!"=="Y" (
            git init
            echo [OK] Git repository initialized.
            echo.
        ) else (
            echo [ABORTED] Please run this installer inside a Git repository.
            echo.
            pause
            exit /b 1
        )
    )
)

REM Run CommitGuard --install
%PYTHON_CMD% "%~dp0commitguard.py" --install
if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] CommitGuard installation failed.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo ====================================================
echo  CommitGuard is ready to protect your commits!
echo ====================================================
echo.
pause
