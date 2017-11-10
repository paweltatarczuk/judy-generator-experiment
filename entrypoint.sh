#!/bin/bash

if [ "$1" == "bash" ]; then
  exec "$@"
else
  exec python run.py "$@"
fi
