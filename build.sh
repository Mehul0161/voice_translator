#!/usr/bin/env bash
# exit on error
set -o errexit

# Install system dependencies
apt-get update
apt-get install -y python3-dev build-essential

# Upgrade pip and install wheel
python -m pip install --upgrade pip
pip install wheel setuptools

# Install Python dependencies
pip install --no-cache-dir -r requirements.txt 