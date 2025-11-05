#!/usr/bin/env bash
# exit on error
set -o errexit

echo "Installing system dependencies..."
# Skipping apt operations on Render (read-only filesystem during build)

echo "Upgrading pip and installing wheel..."
python -m pip install --upgrade pip
pip install wheel setuptools

echo "Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt

echo "Build completed successfully!"
