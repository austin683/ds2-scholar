#!/usr/bin/env bash
# DS2 Scholar — stop backend + frontend

stop_port() {
    local port=$1
    local pids
    pids=$(lsof -ti tcp:"$port" 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "Stopping process(es) on port $port (PID $pids)"
        kill "$pids" 2>/dev/null
    else
        echo "Nothing running on port $port"
    fi
}

stop_port 8001   # backend
stop_port 3001   # frontend (React dev server)

echo "Done."
