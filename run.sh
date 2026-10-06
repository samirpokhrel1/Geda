#!/usr/bin/env bash
# One-command launcher: creates a virtualenv, installs Flask, starts the app.
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then python3 -m venv .venv; fi
. .venv/bin/activate
pip install -q -r requirements.txt
python app.py "$@"
