"""
Pytest configuration and shared fixtures for e2e tests.

This module provides:
- Application startup/shutdown fixtures
- Browser configuration for Playwright
- Test data fixtures
- Utility functions for testing
"""
import os
import sys
import time
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Generator, Optional
import pytest
from playwright.sync_api import Page, BrowserContext, Browser, expect

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test configuration
TEST_HOST = os.getenv("E2A_TEST_HOST", "127.0.0.1")
TEST_PORT = int(os.getenv("E2A_TEST_PORT", "7860"))
TEST_URL = f"http://{TEST_HOST}:{TEST_PORT}"
APP_STARTUP_TIMEOUT = 60  # seconds
APP_STARTUP_CHECK_INTERVAL = 0.5  # seconds


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return PROJECT_ROOT / "tools" / "workflow-testing"


@pytest.fixture(scope="session")
def test_ebook_txt(test_data_dir: Path) -> Path:
    """Return path to test English text file."""
    return test_data_dir / "test1.txt"


@pytest.fixture(scope="session")
def test_voice_file() -> Path:
    """Return path to test voice file."""
    return PROJECT_ROOT / "voices" / "eng" / "elder" / "male" / "DavidAttenborough.wav"


@pytest.fixture(scope="session")
def output_dir() -> Generator[Path, None, None]:
    """Create and cleanup temporary output directory for tests."""
    with tempfile.TemporaryDirectory(prefix="e2a_test_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture(scope="session")
def app_process() -> Generator[subprocess.Popen, None, None]:
    """
    Start the ebook2audiobook application and yield the process.
    Automatically shuts down after all tests complete.

    The application is started once for the entire test session to improve performance.
    """
    # Check if app is already running
    if _is_app_running():
        print(f"\n✓ Application already running at {TEST_URL}")
        yield None
        return

    print(f"\n🚀 Starting ebook2audiobook application on {TEST_URL}...")

    # Start the application
    env = os.environ.copy()
    env["GRADIO_SERVER_NAME"] = TEST_HOST
    env["GRADIO_SERVER_PORT"] = str(TEST_PORT)

    # Use the launcher script if available, otherwise run app.py directly
    launcher = PROJECT_ROOT / "ebook2audiobook.sh"
    if launcher.exists() and os.name != "nt":
        cmd = [str(launcher)]
    else:
        cmd = [sys.executable, str(PROJECT_ROOT / "app.py")]

    process = subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(PROJECT_ROOT),
        preexec_fn=None if os.name == "nt" else os.setsid
    )

    # Wait for application to be ready
    start_time = time.time()
    while time.time() - start_time < APP_STARTUP_TIMEOUT:
        if _is_app_running():
            print(f"✓ Application started successfully in {time.time() - start_time:.1f}s")
            break

        # Check if process crashed
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            raise RuntimeError(
                f"Application failed to start:\n"
                f"STDOUT: {stdout.decode()}\n"
                f"STDERR: {stderr.decode()}"
            )

        time.sleep(APP_STARTUP_CHECK_INTERVAL)
    else:
        # Timeout - kill process and raise error
        _kill_process(process)
        raise TimeoutError(
            f"Application did not start within {APP_STARTUP_TIMEOUT}s timeout"
        )

    yield process

    # Cleanup - shutdown application
    print("\n🛑 Shutting down application...")
    _kill_process(process)

    # Wait for process to terminate
    try:
        process.wait(timeout=10)
        print("✓ Application shut down cleanly")
    except subprocess.TimeoutExpired:
        print("⚠ Application did not shut down gracefully, forcing...")
        process.kill()
        process.wait()


def _is_app_running() -> bool:
    """Check if the application is running and responding."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = sock.connect_ex((TEST_HOST, TEST_PORT))
        return result == 0
    finally:
        sock.close()


def _kill_process(process: subprocess.Popen) -> None:
    """Kill a process and its children."""
    if os.name == "nt":
        # Windows
        process.terminate()
    else:
        # Unix - kill process group
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except ProcessLookupError:
            pass


@pytest.fixture
def page(
    app_process: Optional[subprocess.Popen],
    context: BrowserContext
) -> Generator[Page, None, None]:
    """
    Create a new browser page for each test.
    Navigates to the application and waits for it to load.
    """
    page = context.new_page()

    # Navigate to application
    page.goto(TEST_URL, wait_until="networkidle", timeout=30000)

    # Wait for Gradio to be fully loaded
    # Gradio adds a "gradio-app" class when ready
    page.wait_for_selector(".gradio-container", timeout=30000)

    yield page

    # Cleanup
    page.close()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    """Configure browser context for Playwright tests."""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "record_video_dir": None,  # Set to path to record videos
        "record_video_size": {"width": 1920, "height": 1080},
    }


# Helper functions for tests

def wait_for_conversion_complete(
    page: Page,
    timeout: int = 300
) -> None:
    """
    Wait for conversion to complete by monitoring the progress indicator.

    Args:
        page: Playwright page object
        timeout: Maximum time to wait in seconds

    Raises:
        TimeoutError: If conversion doesn't complete within timeout
    """
    # Implementation depends on how Gradio shows progress
    # This is a placeholder - will be refined in RED phase
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check for completion indicators
        # TODO: Implement based on actual Gradio UI elements
        time.sleep(1)


def get_conversion_status(page: Page) -> str:
    """
    Get current conversion status from the UI.

    Returns:
        Status string (e.g., "idle", "converting", "completed", "error")
    """
    # TODO: Implement based on actual Gradio UI
    return "unknown"


def upload_file(page: Page, file_path: Path, input_selector: str) -> None:
    """
    Upload a file using Gradio's file input.

    Args:
        page: Playwright page object
        file_path: Path to file to upload
        input_selector: CSS selector for file input
    """
    file_input = page.locator(input_selector)
    file_input.set_input_files(str(file_path))


def wait_for_element_text(
    page: Page,
    selector: str,
    expected_text: str,
    timeout: int = 10
) -> None:
    """
    Wait for an element to contain expected text.

    Args:
        page: Playwright page object
        selector: CSS selector for element
        expected_text: Expected text content
        timeout: Maximum time to wait in seconds
    """
    locator = page.locator(selector)
    expect(locator).to_contain_text(expected_text, timeout=timeout * 1000)
