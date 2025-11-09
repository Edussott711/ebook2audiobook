#!/bin/bash
set -e

echo "🚀 Running post-create setup..."

# Install project dependencies
if [ -f "requirements.txt" ]; then
    echo "📦 Installing project dependencies..."
    pip install --user -r requirements.txt
fi

# Install development dependencies
if [ -f "requirements-dev.txt" ]; then
    echo "📦 Installing development dependencies..."
    pip install --user -r requirements-dev.txt
fi

# Install project in editable mode
if [ -f "setup.py" ]; then
    echo "📦 Installing project in editable mode..."
    pip install --user -e .
fi

# Install pre-commit hooks
if [ -f ".pre-commit-config.yaml" ]; then
    echo "🪝 Installing pre-commit hooks..."
    pre-commit install
fi

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p audiobooks/{cli,gui} ebooks/tests models voices tmp logs tests

# Setup git config if not already configured
if [ -z "$(git config --global user.name)" ]; then
    echo "⚙️  Setting up git configuration..."
    git config --global --add safe.directory /workspace
fi

echo "✅ Post-create setup completed!"
echo ""
echo "🎉 Development environment is ready to use!"
echo ""
echo "📚 Available commands:"
echo "  - pytest                  # Run tests"
echo "  - black .                 # Format code"
echo "  - flake8 .                # Lint code"
echo "  - mypy .                  # Type check"
echo "  - pre-commit run --all-files  # Run all pre-commit hooks"
echo "  - python app.py           # Run the application"
echo ""
