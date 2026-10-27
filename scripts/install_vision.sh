#!/usr/bin/env bash
set -euo pipefail
python -m pip install --index-url https://download.pytorch.org/whl/cpu \
  'torch==2.14.1+cpu' 'torchvision==0.29.1+cpu'
