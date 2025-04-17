#!/bin/bash
if [[ "$1" == "--dummy" ]]; then
    python3 main.py --dummy
else
    python3 main.py
fi
