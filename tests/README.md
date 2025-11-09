# E2E Tests for ebook2audiobook

This directory contains end-to-end (e2e) tests for the ebook2audiobook web interface using Playwright and pytest.

## 🎯 Test Philosophy: Red-Green-Refactor (TDD)

These tests follow **Test-Driven Development** methodology:

### 🔴 RED Phase (Current)
Tests are written to **expose production readiness issues**:
- Missing UI test identifiers (`data-testid` attributes)
- Unclear error messages
- Missing progress indicators
- Session management gaps
- Security vulnerabilities
- Resource management issues

**These tests WILL FAIL initially** - this is intentional! They document what production-ready software should do.

### 🟢 GREEN Phase
After running tests and seeing failures, we implement the minimum necessary code to make tests pass:
- Add `data-testid` attributes to UI components
- Implement proper error handling
- Add progress indicators
- Fix session persistence
- Add input validation
- Improve accessibility

### 🔄 REFACTOR Phase
Once tests pass, we refactor for quality:
- Clean up code
- Improve performance
- Enhance user experience
- Add polish and edge case handling

## 📁 Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── e2e/
│   ├── test_basic_conversion.py      # Core conversion flow tests
│   ├── test_session_persistence.py   # Session management tests
│   └── test_error_handling.py        # Error cases and edge conditions
└── README.md                      # This file
```

## 🚀 Running Tests

### Prerequisites

1. Install test dependencies:
```bash
pip install -r requirements-test.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

### Run All Tests

```bash
# Run all e2e tests
pytest tests/e2e/

# Run with verbose output
pytest tests/e2e/ -v

# Run specific test file
pytest tests/e2e/test_basic_conversion.py

# Run specific test
pytest tests/e2e/test_basic_conversion.py::test_application_loads_successfully
```

### Run by Marker (Category)

```bash
# Only critical tests
pytest -m critical

# Only smoke tests (fast, basic checks)
pytest -m smoke

# Only session-related tests
pytest -m session

# Only error handling tests
pytest -m error_handling

# Exclude slow tests
pytest -m "not slow"
```

### Parallel Execution

```bash
# Run tests in parallel (faster)
pytest tests/e2e/ -n auto
```

### Generate HTML Report

```bash
# Generate HTML report
pytest tests/e2e/ --html=test-report.html --self-contained-html
```

### Run with Coverage

```bash
# Run with code coverage
pytest tests/e2e/ --cov=lib --cov-report=html
```

## 🏷️ Test Markers

Tests are organized with markers for easy filtering:

- `@pytest.mark.critical` - Must pass for production
- `@pytest.mark.smoke` - Quick sanity checks
- `@pytest.mark.slow` - Long-running tests (>30s)
- `@pytest.mark.conversion` - Conversion functionality
- `@pytest.mark.session` - Session management
- `@pytest.mark.ui` - UI interaction tests
- `@pytest.mark.error_handling` - Error scenarios
- `@pytest.mark.security` - Security-related tests
- `@pytest.mark.performance` - Performance tests

## 📊 Test Coverage Goals

### Critical User Flows (Must be tested)
- ✅ Basic ebook upload and conversion
- ✅ Session resumption after disconnect
- ✅ Error handling and recovery
- ✅ Progress tracking
- ✅ File download

### Important Flows (Should be tested)
- ✅ Multi-language support
- ✅ TTS engine selection
- ✅ Voice selection
- ✅ Output format selection
- ⏳ Batch conversion (TODO)
- ⏳ Voice cloning (TODO)

### Nice-to-Have (Optional)
- ⏳ Custom model upload
- ⏳ Performance under load
- ⏳ Mobile responsiveness

## 🐛 Expected Failures (RED Phase)

The following tests are **expected to fail** initially:

### Missing UI Test IDs
Most tests will fail because Gradio components lack `data-testid` attributes:
```python
# WILL FAIL: Element not found
file_upload = page.locator('[data-testid="ebook-file-upload"]')
```

**Fix:** Add `elem_id` parameter to Gradio components in `lib/functions.py`:
```python
gr.File(label="Upload Ebook", elem_id="ebook-file-upload")
```

### Missing Features
Some tests document features that don't exist yet:
- Session list/management UI
- Cancel button during conversion
- Disk space warnings
- Model download progress
- Queue management for concurrent conversions

**Fix:** Implement these features or mark tests as `@pytest.mark.skip` with reason.

### Unclear Error Messages
Tests check for user-friendly error messages:
```python
# WILL FAIL: Technical error exposed
assert "NoneType object" not in error_text
```

**Fix:** Wrap exceptions and show user-friendly messages.

## 🔧 Configuration

### Environment Variables

```bash
# Change test target
export E2A_TEST_HOST=127.0.0.1
export E2A_TEST_PORT=7860

# Playwright options
export PLAYWRIGHT_BROWSER=chromium  # or firefox, webkit
```

### Pytest Configuration

See `pytest.ini` for:
- Test discovery patterns
- Default markers
- Timeout settings
- Coverage configuration

## 📝 Writing New Tests

### Test Template

```python
import pytest
from playwright.sync_api import Page, expect

@pytest.mark.critical  # Add appropriate markers
@pytest.mark.conversion
def test_my_new_feature(page: Page, test_ebook_txt: Path):
    """
    Test description.

    PRODUCTION REQUIREMENT: What must work for production.
    """
    # Arrange
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    # Act
    convert_button = page.locator('[data-testid="convert-button"]')
    convert_button.click()

    # Assert
    success_message = page.locator('[data-testid="conversion-complete"]')
    expect(success_message).to_be_visible(timeout=60000)
```

### Best Practices

1. **Use data-testid**: Always use `data-testid` attributes for stability
2. **Clear assertions**: Use Playwright's `expect()` API
3. **Proper timeouts**: Set appropriate timeouts for async operations
4. **Cleanup**: Use fixtures for automatic cleanup
5. **Independence**: Tests should not depend on each other
6. **Documentation**: Include "PRODUCTION REQUIREMENT" comment

## 🚨 Troubleshooting

### Application won't start

```bash
# Check if port is in use
lsof -i :7860

# Kill existing process
kill -9 <PID>

# Or use different port
export E2A_TEST_PORT=7861
```

### Tests timeout

- Increase timeout in `pytest.ini`
- Check application logs for errors
- Verify network connectivity

### Browser issues

```bash
# Reinstall browsers
playwright install --force chromium

# Use headed mode for debugging
pytest tests/e2e/ --headed

# Slow down execution
pytest tests/e2e/ --slowmo=1000
```

### Can't find elements

- Use headed mode to inspect UI
- Use Playwright inspector:
```bash
PWDEBUG=1 pytest tests/e2e/test_basic_conversion.py::test_application_loads_successfully
```

## 📈 CI/CD Integration

### GitHub Actions

Add to `.github/workflows/e2e-tests.yml`:

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
          playwright install chromium

      - name: Run E2E tests
        run: pytest tests/e2e/ -m "critical and not slow"

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test-report.html
```

## 🎯 Success Criteria

The test suite is considered successful when:

1. **All critical tests pass** (`pytest -m critical`)
2. **No security vulnerabilities** (`pytest -m security`)
3. **Error handling is comprehensive** (`pytest -m error_handling`)
4. **Session management is robust** (`pytest -m session`)
5. **Code coverage > 70%** for core conversion logic

## 📚 Resources

- [Playwright Documentation](https://playwright.dev/python/)
- [pytest Documentation](https://docs.pytest.org/)
- [Gradio Testing Guide](https://www.gradio.app/guides/testing)
- [Test-Driven Development](https://en.wikipedia.org/wiki/Test-driven_development)

## 🤝 Contributing

When adding new features:

1. **Write tests first** (RED)
2. **Implement minimum code** to pass (GREEN)
3. **Refactor** for quality (REFACTOR)
4. Update this README if adding new test categories

---

**Remember:** Failing tests are not failures - they're documentation of what needs to be built! 🎯
