#!/bin/bash
cd "$(dirname "$0")"

# Matar instancia anterior si existe
pkill -f "python3.*reel-gui.py" 2>/dev/null || true
sleep 0.5

# Iniciar servidor
python3 reel-gui.py &
SERVER_PID=$!

sleep 1

# Abrir navegador
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8080
elif command -v google-chrome &> /dev/null; then
    google-chrome http://localhost:8080
elif command -v chromium-browser &> /dev/null; then
    chromium-browser http://localhost:8080
fi

wait $SERVER_PID
