#!/usr/bin/env bash
# DS2 Scholar — stop backend + frontend

stop_port() {
    local port=$1
    local pids
    pids=$(lsof -ti tcp:"$port" 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "Stopping process(es) on port $port (PID $pids)"
        kill $pids 2>/dev/null
    else
        echo "Nothing running on port $port"
    fi
}

stop_by_pattern() {
    local label=$1
    local pattern=$2
    local pids
    pids=$(pgrep -f "$pattern" 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "Stopping orphaned $label process(es) (PID $pids)"
        kill $pids 2>/dev/null
    fi
}

stop_port 8001   # backend
stop_port 3001   # frontend (React dev server)

# Catch orphans that aren't bound to those ports
stop_by_pattern "uvicorn/backend" "uvicorn backend.main"
stop_by_pattern "React dev server" "react-scripts start"

echo "Done."
