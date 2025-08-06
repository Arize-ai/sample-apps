#!/bin/bash

# exit when any command fails
set -e

pip_version=25.1.1
ruff_version=0.12.2

msg="""
To use this script you need to install dependencies as follows:\n
    1. python -m pip install --upgrade pip==${pip_version}\n
    2. pip install ruff==${ruff_version}
"""
echo -e $msg

echo " "
echo "ruff format"
echo "=========="
ruff format
echo " "
echo "ruff check"
echo "=========="
ruff check --fix