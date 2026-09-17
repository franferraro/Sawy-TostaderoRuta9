#!/bin/zsh

cd "$(dirname "$0")"

python3 run_all.py

if lsof -i :8000 >/dev/null 2>&1; then
  open "http://localhost:8000/app_runtime/index.html"
else
  python3 -m http.server 8000 >/tmp/sawy_tostadero_ruta9.log 2>&1 &
  sleep 1
  open "http://localhost:8000/app_runtime/index.html"
fi
