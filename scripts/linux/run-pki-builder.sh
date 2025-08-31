#!/usr/bin/env bash
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
ROOT_DIR="$SCRIPT_DIR/../.."
SOURCE_DIR="$ROOT_DIR/src"

pushd "$SOURCE_DIR"

PYTHON="$ROOT_DIR/env/python-3.12.10-embed-amd64-linux/bin/python3.12"
ENTRYPOINT="main.py"

"$PYTHON" "$ENTRYPOINT" "$@"

popd
