#!/usr/bin/env bash
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
ROOT_DIR="$SCRIPT_DIR/../.."

pushd "$ROOT_DIR"

PYTHON="$ROOT_DIR/env/python-3.12.10-embed-amd64-linux/bin/python3.12"
UPDATE_ARGS="-m poetry install --no-root"

export POETRY_VIRTUALENVS_CREATE=false

"$PYTHON" $UPDATE_ARGS

popd

