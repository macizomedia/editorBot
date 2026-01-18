#!/bin/bash
# Setup script for editorBot deployment

set -e

echo "🚀 EditorBot Setup Script"
echo "========================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "📦 Checking Python version..."
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.10"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$REQUIRED_VERSION" ]; then
    echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION (required: $REQUIRED_VERSION+)"
else
    echo -e "${RED}✗${NC} Python $PYTHON_VERSION (required: $REQUIRED_VERSION+)"
    exit 1
fi

# Check if in editorBot directory
if [ ! -f "pyproject.toml" ] || [ ! -d "bot" ]; then
    echo -e "${RED}✗${NC} Please run this script from the editorBot directory"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📁 Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
else
    echo -e "${YELLOW}⚠${NC} Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "🔄 Upgrading pip..."
pip install --upgrade pip setuptools wheel > /dev/null

# Install dialect_mediator FIRST (it has no external deps)
echo "📦 Installing dialect_mediator..."
if [ -d "../dialect_mediator" ]; then
    pip install -e ../dialect_mediator
    echo -e "${GREEN}✓${NC} dialect_mediator installed"
else
    echo -e "${RED}✗${NC} ../dialect_mediator not found"
    exit 1
fi

# Install editorBot and its dependencies
echo "📦 Installing editorBot..."
pip install -e .
echo -e "${GREEN}✓${NC} editorBot installed"

# Setup .env file
if [ ! -f ".env" ]; then
    echo "🔐 Creating .env file..."
    cp .env.example .env
    echo -e "${YELLOW}⚠${NC} .env file created. Please edit it with your credentials:"
    echo ""
    cat .env.example
    echo ""
else
    echo -e "${GREEN}✓${NC} .env file already exists"
fi

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your credentials:"
echo "   nano .env"
echo ""
echo "2. Test the setup:"
echo "   python -m bot.bot"
echo ""
echo "3. For EC2/systemd deployment, see README.md"
echo ""
