#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════
# Lead Radar Launcher (Shell Script)
# ═══════════════════════════════════════════════════════════════════════

# Colors for terminal output
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"
echo -e "Starting Lead Radar Platform..."
echo -e "${CYAN}══════════════════════════════════════════════════════════════${NC}"

# ── Environment Setup ──────────────────────────────────────────────────

# 1. Check for Python Virtual Environment
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating venv...${NC}"
    python -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to create venv. Make sure Python is installed.${NC}"
        exit 1
    fi
    
    # Detect pip path
    if [ -f "venv/Scripts/pip" ]; then PIP_EXE="venv/Scripts/pip"; else PIP_EXE="venv/bin/pip"; fi
    
    echo -e "${YELLOW}Installing backend dependencies...${NC}"
    $PIP_EXE install -r backend/requirements.txt
    $PIP_EXE install playwright
    venv/Scripts/python -m playwright install chromium
fi

# 2. Check for Frontend Dependencies
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}Frontend dependencies not found. Running npm install...${NC}"
    (cd frontend && npm install)
fi

# 3. Detect Python executable path for running
if [ -f "venv/Scripts/python" ]; then
    PYTHON_EXE="../venv/Scripts/python"
elif [ -f "venv/bin/python" ]; then
    PYTHON_EXE="../venv/bin/python"
else
    PYTHON_EXE="python"
fi

# Cleanup function to kill background processes on exit
cleanup() {
    echo -e "\n${YELLOW}Stopping servers...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit
}

# Trap Ctrl+C (SIGINT) and terminal close (SIGTERM)
trap cleanup SIGINT SIGTERM

# 1. Start Backend
echo -e "${CYAN}[1/2] Starting Backend (FastAPI)...${NC}"
(cd backend && $PYTHON_EXE server.py) &
BACKEND_PID=$!

# 2. Start Frontend
echo -e "${CYAN}[2/2] Starting Frontend (Next.js)...${NC}"
(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo -e "\n${GREEN}✔ Backend running at: http://localhost:8000${NC}"
echo -e "${GREEN}✔ Frontend running at: http://localhost:3000${NC}"
echo -e "\n${YELLOW}Press Ctrl+C to stop both servers.${NC}"

# Wait for background processes
wait $BACKEND_PID $FRONTEND_PID
