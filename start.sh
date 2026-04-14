#!/bin/bash
# ============================================================
# VetClaim AI — Start all services with one command
#
# Usage:  ./start.sh
#   Starts:
#     Backend API    → http://localhost:5001
#     Frontend       → http://localhost:5173
#     VA Portal      → http://localhost:5050
#
# Press Ctrl+C once to stop everything.
# ============================================================

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Colours
RESET="\033[0m"
BOLD="\033[1m"
GOLD="\033[33m"
BLUE="\033[34m"
GREEN="\033[32m"
CYAN="\033[36m"
RED="\033[31m"

echo -e "${BOLD}${GOLD}"
echo "  ██╗   ██╗███████╗████████╗ ██████╗██╗      █████╗ ██╗███╗   ███╗"
echo "  ██║   ██║██╔════╝╚══██╔══╝██╔════╝██║     ██╔══██╗██║████╗ ████║"
echo "  ██║   ██║█████╗     ██║   ██║     ██║     ███████║██║██╔████╔██║"
echo "  ╚██╗ ██╔╝██╔══╝     ██║   ██║     ██║     ██╔══██║██║██║╚██╔╝██║"
echo "   ╚████╔╝ ███████╗   ██║   ╚██████╗███████╗██║  ██║██║██║ ╚═╝ ██║"
echo "    ╚═══╝  ╚══════╝   ╚═╝    ╚═════╝╚══════╝╚═╝  ╚═╝╚═╝╚═╝     ╚═╝"
echo -e "${RESET}"
echo -e "  ${BOLD}Starting all VetClaim AI services…${RESET}"
echo ""
echo -e "  ${GREEN}●${RESET} Backend API   → ${CYAN}http://localhost:5001${RESET}"
echo -e "  ${GREEN}●${RESET} Frontend      → ${CYAN}http://localhost:5173${RESET}"
echo -e "  ${GREEN}●${RESET} VA Portal     → ${CYAN}http://localhost:5050${RESET}"
echo ""
echo -e "  Press ${BOLD}Ctrl+C${RESET} to stop all services."
echo "  ──────────────────────────────────────────────────────"
echo ""

# Helper to kill processes on a port
kill_ports() {
  for port in 5001 5050 5173; do
    local pids=$(lsof -t -i:$port 2>/dev/null)
    if [ -n "$pids" ]; then
      echo -e "  ${RED}Port $port is in use. Killing process(es): $pids${RESET}"
      echo "$pids" | xargs kill -9 2>/dev/null
      sleep 0.5
    fi
  done
}

kill_ports

# ── Python virtual environment ──────────────────────────────
VENV_DIR="$ROOT/venv"
if command -v python3 &>/dev/null; then
  PY_BIN="python3"
else
  echo -e "  ${RED}Python 3 not found. Please install Python 3.${RESET}"
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  echo -e "  ${GOLD}No venv found — creating one and installing dependencies…${RESET}"
  $PY_BIN -m venv "$VENV_DIR"
  "$VENV_DIR/bin/pip" install --quiet -r "$ROOT/requirements.txt"
  echo -e "  ${GREEN}Dependencies installed.${RESET}\n"
fi

# Use venv python
PYTHON="$VENV_DIR/bin/python3"
[ ! -f "$PYTHON" ] && PYTHON="$VENV_DIR/Scripts/python"

# Kill all child processes on exit
cleanup() {
  echo ""
  echo -e "  ${RED}Stopping all services…${RESET}"
  jobs -p | xargs -r kill 2>/dev/null
  wait 2>/dev/null
  echo -e "  ${GOLD}All services stopped. Goodbye!${RESET}"
  exit 0
}
trap cleanup INT TERM

# ── Backend (Flask, port 5001) ───────────────────────────────
(
  cd "$ROOT/backend"
  echo -e "[${BLUE}backend${RESET}]   Starting Flask API on :5001…"
  $PYTHON server.py 2>&1 | sed "s/^/  [backend]  /"
) &

# ── Mock VA Portal (Flask, port 5050) ───────────────────────
(
  cd "$ROOT/mock_va_portal"
  echo -e "[${GREEN}va-portal${RESET}] Starting Mock VA Portal on :5050…"
  $PYTHON server.py 2>&1 | sed "s/^/  [va-portal] /"
) &

# ── Frontend (Vite, port 5173) ──────────────────────────────
(
  cd "$ROOT/frontend"
  if [ ! -d "node_modules" ]; then
    echo -e "[${GOLD}frontend${RESET}]  Installing npm dependencies…"
    npm install 2>&1 | sed "s/^/  [frontend]  /"
  fi
  echo -e "[${GOLD}frontend${RESET}]  Starting Vite dev server on :5173…"
  npm run dev 2>&1 | sed "s/^/  [frontend]  /"
) &

# ── Wait for servers to be ready, then open browsers ────────
echo -e "\n  Waiting for servers to start..."
for url in "http://localhost:5173" "http://localhost:5050"; do
  for i in $(seq 1 30); do
    if curl -s -o /dev/null "$url"; then
      break
    fi
    sleep 1
  done
done

echo -e "  ${GREEN}✔${RESET} Servers are ready. Opening browsers..."
open "http://localhost:5173"
open "http://localhost:5050"

# Wait for all background jobs — stays alive until Ctrl+C
wait
