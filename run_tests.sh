#!/bin/bash
# E2E Test Runner for ebook2audiobook
# Convenience script for running tests with common configurations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if virtual environment is active
if [[ -z "$VIRTUAL_ENV" ]]; then
    print_warning "No virtual environment detected. It's recommended to use a venv."
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Parse arguments
MODE=${1:-all}

case "$MODE" in
    "smoke")
        print_header "Running Smoke Tests (Fast Sanity Checks)"
        pytest tests/e2e/ -m smoke -v
        ;;

    "critical")
        print_header "Running Critical Tests (Must Pass for Production)"
        pytest tests/e2e/ -m critical -v
        ;;

    "fast")
        print_header "Running Fast Tests (Excluding Slow Tests)"
        pytest tests/e2e/ -m "not slow" -v
        ;;

    "session")
        print_header "Running Session Management Tests"
        pytest tests/e2e/test_session_persistence.py -v
        ;;

    "error")
        print_header "Running Error Handling Tests"
        pytest tests/e2e/test_error_handling.py -v
        ;;

    "conversion")
        print_header "Running Basic Conversion Tests"
        pytest tests/e2e/test_basic_conversion.py -v
        ;;

    "security")
        print_header "Running Security Tests"
        pytest tests/e2e/ -m security -v
        ;;

    "parallel")
        print_header "Running All Tests in Parallel"
        pytest tests/e2e/ -n auto -v
        ;;

    "coverage")
        print_header "Running Tests with Coverage Report"
        pytest tests/e2e/ --cov=lib --cov-report=html --cov-report=term -v
        print_success "Coverage report generated in htmlcov/index.html"
        ;;

    "report")
        print_header "Running Tests with HTML Report"
        pytest tests/e2e/ --html=test-report.html --self-contained-html -v
        print_success "Test report generated: test-report.html"
        ;;

    "debug")
        print_header "Running Tests in Debug Mode (Headed Browser)"
        pytest tests/e2e/ --headed --slowmo=500 -v -s
        ;;

    "install")
        print_header "Installing Test Dependencies"
        pip install -r requirements-test.txt
        playwright install chromium
        print_success "Test dependencies installed"
        ;;

    "setup")
        print_header "Setting Up Test Environment"
        echo "1. Installing test dependencies..."
        pip install -r requirements-test.txt

        echo "2. Installing Playwright browsers..."
        playwright install chromium

        echo "3. Verifying installation..."
        python -c "import pytest; import playwright; print('✓ pytest and playwright installed')"

        print_success "Test environment ready!"
        ;;

    "ci")
        print_header "Running CI Test Suite (Critical Tests Only)"
        pytest tests/e2e/ -m "critical and not slow" -v --tb=short
        ;;

    "all"|"")
        print_header "Running All E2E Tests"
        pytest tests/e2e/ -v
        ;;

    "help"|"-h"|"--help")
        echo "E2E Test Runner for ebook2audiobook"
        echo ""
        echo "Usage: ./run_tests.sh [MODE]"
        echo ""
        echo "Available modes:"
        echo "  all          - Run all tests (default)"
        echo "  smoke        - Run quick smoke tests"
        echo "  critical     - Run critical tests only"
        echo "  fast         - Run all tests except slow ones"
        echo "  session      - Run session management tests"
        echo "  error        - Run error handling tests"
        echo "  conversion   - Run conversion tests"
        echo "  security     - Run security tests"
        echo "  parallel     - Run tests in parallel (faster)"
        echo "  coverage     - Run with coverage report"
        echo "  report       - Generate HTML test report"
        echo "  debug        - Run with visible browser (debugging)"
        echo "  install      - Install test dependencies"
        echo "  setup        - Full test environment setup"
        echo "  ci           - Run CI test suite"
        echo "  help         - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./run_tests.sh smoke           # Quick sanity check"
        echo "  ./run_tests.sh critical        # Production readiness"
        echo "  ./run_tests.sh debug           # Visual debugging"
        echo "  ./run_tests.sh coverage        # With coverage report"
        exit 0
        ;;

    *)
        print_error "Unknown mode: $MODE"
        echo "Run './run_tests.sh help' for usage information"
        exit 1
        ;;
esac

# Check exit code
if [ $? -eq 0 ]; then
    print_success "Tests completed successfully!"
    exit 0
else
    print_error "Some tests failed. See output above for details."
    exit 1
fi
