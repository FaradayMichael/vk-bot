#!/bin/bash

handle_term() { 
  echo "Caught SIGTERM signal!"
  
  if [ "${parser_child}" ]; then
    echo "Killing parser ${parser_child}"
    kill -s SIGTERM $parser_child 2>&1
  fi
}

trap 'handle_term' SIGINT SIGTERM

Xvfb :0 -nolock -screen 0 1920x1280x24 &
xvfb_child=$!
echo "Xvfb PID ${xvfb_child}"

export DISPLAY=:0.0
pytest -s tests$ONLY

kill -SIGTERM $xvfb_child