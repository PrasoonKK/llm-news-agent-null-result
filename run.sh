#!/bin/bash
cd "$(dirname "$0")"

trap 'kill $API_PID $UI_PID 2>/dev/null; echo "Stopped."; exit' INT TERM

uvicorn api:app --port 8000 &
API_PID=$!

cd dashboard && npm run dev &
UI_PID=$!

echo ""
echo "  EP Engine running → http://localhost:5174"
echo "  Press Ctrl+C to stop."
echo ""

wait
