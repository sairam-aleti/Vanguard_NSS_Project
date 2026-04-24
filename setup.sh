#!/bin/bash
# ═══════════════════════════════════════════════════════════
#  Project Vanguard — One-Click Setup (Linux/Mac)
# ═══════════════════════════════════════════════════════════
#  Run this script after cloning the repo:
#    chmod +x setup.sh && ./setup.sh
# ═══════════════════════════════════════════════════════════

set -e

echo ""
echo "═══════════════════════════════════════════════════"
echo "  PROJECT VANGUARD — Automated Setup"
echo "  Secure Logistics & Supply Chain Defense"
echo "═══════════════════════════════════════════════════"
echo ""

# Check Python
echo "[1/4] Checking Python installation..."
if command -v python3 &>/dev/null; then
    PY=python3
    echo "       Found: $(python3 --version)"
elif command -v python &>/dev/null; then
    PY=python
    echo "       Found: $(python --version)"
else
    echo "       ERROR: Python not found! Install Python 3.10+"
    exit 1
fi

# Create virtual environment
echo "[2/4] Creating virtual environment..."
if [ -d "venv" ]; then
    echo "       Already exists. Reusing."
else
    $PY -m venv venv
    echo "       Created: ./venv/"
fi

# Install dependencies
echo "[3/4] Installing dependencies..."
source venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "       Done."

# Initialize database
echo "[4/4] Initializing database & encryption..."
python db_setup.py

echo ""
echo "═══════════════════════════════════════════════════"
echo "  SETUP COMPLETE!"
echo "═══════════════════════════════════════════════════"
echo ""
echo "  To run:  ./run.sh"
echo ""
