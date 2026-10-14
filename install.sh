#!/usr/bin/env bash
# ==============================================================================
# CommitGuard Installer for Linux and macOS
# ==============================================================================

set -e

CYAN='\033[1;36m'
GREEN='\033[1;32m'
RED='\033[1;31m'
YELLOW='\033[1;33m'
RESET='\033[0m'

echo -e "${CYAN}====================================================${RESET}"
echo -e "${CYAN}     CommitGuard - Git Pre-commit Hook Installer    ${RESET}"
echo -e "${CYAN}====================================================${RESET}"

# Find Python executable
if command -v python3 >/dev/null 2>&1; then
    PYTHON_EXEC="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_EXEC="python"
else
    echo -e "${RED}[Error] Python is not installed or not available in PATH.${RESET}"
    echo "Please install Python 3.8+ to use CommitGuard."
    exit 1
fi

echo -e "Using Python: ${GREEN}$($PYTHON_EXEC --version)${RESET}"

# Verify if current directory is a git repository
if [ ! -d ".git" ] && ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo -e "${YELLOW}[Notice] Current directory is not a Git repository.${RESET}"
    read -p "Would you like to initialize a new git repository now? (y/N): " init_choice
    if [[ "$init_choice" =~ ^[Yy]$ ]]; then
        git init
        echo -e "${GREEN}[OK] Git repository initialized.${RESET}"
    else
        echo -e "${RED}[Aborted] Please run this script inside a Git repository.${RESET}"
        exit 1
    fi
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Run CommitGuard installation command
$PYTHON_EXEC "$SCRIPT_DIR/commitguard.py" --install

echo -e "${GREEN}CommitGuard has been successfully installed as your Git Pre-commit hook!${RESET}"
