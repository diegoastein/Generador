#!/bin/bash
cd "$(dirname "$0")"

# Verificar que node esté disponible
if ! command -v node &> /dev/null; then
    echo "Error: Node.js no está instalado"
    exit 1
fi

# Levantar el servidor en background
node server.js &
SERVER_PID=$!

# Esperar a que el servidor esté listo
sleep 1

# Abrir el browser
if command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8000
elif command -v google-chrome &> /dev/null; then
    google-chrome http://localhost:8000
elif command -v chromium-browser &> /dev/null; then
    chromium-browser http://localhost:8000
fi

# Mantener el servidor corriendo
wait $SERVER_PID
