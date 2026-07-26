#!/bin/bash

set -x
set -e
set -o pipefail

uv venv --python 3.14
uv pip install -r requirements/dev.txt -e .
