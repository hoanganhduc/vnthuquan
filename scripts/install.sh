#!/usr/bin/env bash
set -euo pipefail

VENV_PATH="${VNTHUQUAN_VENV:-$HOME/.vnthuquan}"

python -m venv "$VENV_PATH"
# shellcheck source=/dev/null
source "$VENV_PATH/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install .
vnthuquan --version
