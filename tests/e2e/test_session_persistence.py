"""
E2E Tests for Session Persistence and Recovery

These tests verify that conversion sessions can be resumed after:
- Browser refresh
- Network disconnection
- Application restart (Docker)
- Tab closure and reopening

🔴 RED PHASE: These tests expose session management issues that would cause
production problems where users lose their conversion progress.
"""
import time
import pytest
from pathlib import Path
from playwright.sync_api import Page, expect, BrowserContext


@pytest.mark.critical
@pytest.mark.session
@pytest.mark.slow
def test_session_persists_after_browser_refresh(
    page: Page,
    test_ebook_txt: Path
):
    """
    Test that conversion continues after browser refresh.

    PRODUCTION REQUIREMENT: Users must not lose progress when:
    - Accidentally refreshing page
    - Browser crashes
    - Network briefly disconnects

    This is CRITICAL for long conversions (books taking 30+ minutes).
    """
    # Start conversion
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    convert_button = page.locator('[data-testid="convert-button"]')
    convert_button.click(timeout=5000)

    # Wait for conversion to start
    progress_indicator = page.locator('[data-testid="conversion-progress"]')
    expect(progress_indicator).to_be_visible(timeout=5000)

    # Get initial progress
    progress_percentage = page.locator('[data-testid="progress-percentage"]')
    initial_progress_text = progress_percentage.text_content(timeout=5000)

    # Extract session ID from UI (should be visible for debugging)
    session_id_display = page.locator('[data-testid="session-id"]')
    expect(session_id_display).to_be_visible(timeout=3000)
    session_id = session_id_display.text_content()

    assert session_id and len(session_id) > 0, "Session ID not displayed"

    # Refresh the page (simulate user hitting F5)
    page.reload(wait_until="networkidle")

    # Session should automatically reconnect
    reconnect_message = page.locator('[data-testid="session-reconnected"]')
    expect(reconnect_message).to_be_visible(timeout=10000)

    # Progress should resume from where it was
    progress_indicator = page.locator('[data-testid="conversion-progress"]')
    expect(progress_indicator).to_be_visible(timeout=5000)

    # Session ID should match
    session_id_after_refresh = page.locator('[data-testid="session-id"]').text_content()
    assert session_id == session_id_after_refresh, \
        f"Session ID changed after refresh: {session_id} != {session_id_after_refresh}"

    # Progress should be >= initial progress
    current_progress_text = progress_percentage.text_content(timeout=5000)

    # Parse progress percentages
    import re
    initial_pct = int(re.search(r'(\d+)%', initial_progress_text).group(1))
    current_pct = int(re.search(r'(\d+)%', current_progress_text).group(1))

    assert current_pct >= initial_pct, \
        f"Progress went backwards after refresh: {initial_pct}% -> {current_pct}%"


@pytest.mark.critical
@pytest.mark.session
@pytest.mark.slow
def test_session_list_shows_active_conversions(page: Page, test_ebook_txt: Path):
    """
    Test that users can see list of active/past sessions.

    PRODUCTION REQUIREMENT: Must provide:
    - List of active sessions
    - Session status (running, paused, completed, failed)
    - Ability to resume any active session
    - Session history for last 24 hours
    """
    # Navigate to sessions page/tab
    sessions_tab = page.locator('[data-testid="sessions-tab"]')
    expect(sessions_tab).to_be_visible(timeout=5000)
    sessions_tab.click()

    # Should show empty state initially
    empty_state = page.locator('[data-testid="sessions-empty-state"]')
    # May or may not be visible depending on previous test runs

    # Start a conversion
    page.locator('[data-testid="main-tab"]').click(timeout=3000)

    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    convert_button = page.locator('[data-testid="convert-button"]')
    convert_button.click(timeout=5000)

    # Wait for conversion to start
    time.sleep(3)

    # Go back to sessions tab
    sessions_tab = page.locator('[data-testid="sessions-tab"]')
    sessions_tab.click()

    # Should show active session
    session_list = page.locator('[data-testid="session-list"]')
    expect(session_list).to_be_visible(timeout=5000)

    # At least one session should be listed
    session_items = page.locator('[data-testid^="session-item-"]')
    assert session_items.count() > 0, "No sessions displayed"

    # Each session should show:
    # - Status (running/completed/failed)
    # - Progress percentage
    # - Ebook name
    # - Start time
    # - Action buttons (resume/cancel/delete)

    first_session = session_items.first

    # Status indicator
    status_indicator = first_session.locator('[data-testid="session-status"]')
    expect(status_indicator).to_be_visible(timeout=3000)
    expect(status_indicator).to_contain_text("running", timeout=3000)

    # Progress
    session_progress = first_session.locator('[data-testid="session-progress"]')
    expect(session_progress).to_be_visible(timeout=3000)

    # Ebook name
    session_ebook = first_session.locator('[data-testid="session-ebook-name"]')
    expect(session_ebook).to_contain_text("test1.txt", timeout=3000)

    # Action button
    resume_button = first_session.locator('[data-testid="session-resume-button"]')
    expect(resume_button).to_be_visible(timeout=3000)


@pytest.mark.critical
@pytest.mark.session
def test_resume_session_from_checkpoint(page: Page, test_ebook_txt: Path):
    """
    Test resuming a session from a saved checkpoint.

    PRODUCTION REQUIREMENT: Checkpoints must:
    - Save at key stages (EPUB conversion, chapter extraction, audio generation)
    - Allow resumption from any checkpoint
    - Not duplicate work already done
    - Maintain file integrity
    """
    # Start conversion
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    convert_button = page.locator('[data-testid="convert-button"]')
    convert_button.click(timeout=5000)

    # Wait for first checkpoint
    checkpoint_message = page.locator('[data-testid="checkpoint-saved"]')
    expect(checkpoint_message).to_be_visible(timeout=30000)

    checkpoint_name = checkpoint_message.text_content()
    assert "checkpoint" in checkpoint_name.lower(), \
        "Checkpoint message doesn't indicate checkpoint type"

    # Force stop (simulate crash)
    page.evaluate("() => { window.stop(); }")

    # Refresh page
    page.reload(wait_until="networkidle")

    # Should show resume option
    resume_dialog = page.locator('[data-testid="resume-dialog"]')
    expect(resume_dialog).to_be_visible(timeout=10000)

    resume_button = resume_dialog.locator('[data-testid="resume-button"]')
    expect(resume_button).to_be_visible(timeout=3000)

    # Dialog should show checkpoint info
    expect(resume_dialog).to_contain_text("checkpoint", timeout=3000)
    expect(resume_dialog).to_contain_text("test1.txt", timeout=3000)

    # Resume from checkpoint
    resume_button.click()

    # Conversion should continue
    progress_indicator = page.locator('[data-testid="conversion-progress"]')
    expect(progress_indicator).to_be_visible(timeout=5000)

    # Should not restart from 0%
    progress_text = page.locator('[data-testid="progress-percentage"]').text_content()
    assert "0%" not in progress_text, \
        "Conversion restarted from 0% instead of resuming from checkpoint"


@pytest.mark.critical
@pytest.mark.session
def test_session_cleanup_after_completion(page: Page, test_ebook_txt: Path):
    """
    Test that sessions are properly cleaned up after completion.

    PRODUCTION REQUIREMENT: After conversion completes:
    - Temporary files must be deleted
    - Session state must be marked as completed
    - Resources must be released
    - No zombie processes
    """
    # Complete a conversion
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    convert_button = page.locator('[data-testid="convert-button"]')
    convert_button.click(timeout=5000)

    # Wait for completion
    completion_message = page.locator('[data-testid="conversion-complete"]')
    expect(completion_message).to_be_visible(timeout=120000)

    # Check session status in sessions tab
    sessions_tab = page.locator('[data-testid="sessions-tab"]')
    sessions_tab.click()

    # Find completed session
    session_items = page.locator('[data-testid^="session-item-"]')
    completed_session = session_items.filter(has_text="completed").first
    expect(completed_session).to_be_visible(timeout=5000)

    # Session should show:
    # - "Completed" status
    # - 100% progress
    # - Download button
    # - Delete button (to remove from history)

    status = completed_session.locator('[data-testid="session-status"]')
    expect(status).to_contain_text("completed", timeout=3000)

    progress = completed_session.locator('[data-testid="session-progress"]')
    expect(progress).to_contain_text("100%", timeout=3000)

    download_btn = completed_session.locator('[data-testid="session-download-button"]')
    expect(download_btn).to_be_visible(timeout=3000)

    delete_btn = completed_session.locator('[data-testid="session-delete-button"]')
    expect(delete_btn).to_be_visible(timeout=3000)


@pytest.mark.session
def test_old_sessions_auto_cleanup(page: Page):
    """
    Test that sessions older than 24 hours are automatically cleaned up.

    PRODUCTION REQUIREMENT: Prevent disk space exhaustion:
    - Sessions > 24 hours should be auto-deleted
    - User should be notified before cleanup
    - Option to pin important sessions
    """
    # Navigate to sessions
    sessions_tab = page.locator('[data-testid="sessions-tab"]')
    sessions_tab.click()

    # Check for cleanup notification
    cleanup_message = page.locator('[data-testid="cleanup-notification"]')

    # If old sessions exist, cleanup message should be visible
    # This test may pass without finding old sessions (depends on state)

    # Settings should have cleanup configuration
    settings_button = page.locator('[data-testid="settings-button"]')
    if settings_button.is_visible():
        settings_button.click()

        cleanup_settings = page.locator('[data-testid="cleanup-settings"]')
        expect(cleanup_settings).to_be_visible(timeout=5000)

        # Should show retention period (24 hours)
        expect(cleanup_settings).to_contain_text("24", timeout=3000)


@pytest.mark.critical
@pytest.mark.session
def test_concurrent_sessions_isolated(
    context: BrowserContext,
    test_ebook_txt: Path
):
    """
    Test that multiple concurrent sessions don't interfere with each other.

    PRODUCTION REQUIREMENT: Multi-user support:
    - Sessions must be isolated by user/browser
    - No cross-contamination of data
    - Each session has unique working directory
    - No race conditions
    """
    # Open two tabs
    page1 = context.new_page()
    page2 = context.new_page()

    # Navigate both to app
    page1.goto(f"http://127.0.0.1:7860", wait_until="networkidle")
    page2.goto(f"http://127.0.0.1:7860", wait_until="networkidle")

    # Start conversion in page 1
    file_input1 = page1.locator('input[type="file"]').first
    file_input1.set_input_files(str(test_ebook_txt))

    convert_button1 = page1.locator('[data-testid="convert-button"]')
    convert_button1.click(timeout=5000)

    # Get session ID from page 1
    session_id1 = page1.locator('[data-testid="session-id"]').text_content(timeout=5000)

    # Start conversion in page 2
    file_input2 = page2.locator('input[type="file"]').first
    file_input2.set_input_files(str(test_ebook_txt))

    convert_button2 = page2.locator('[data-testid="convert-button"]')
    convert_button2.click(timeout=5000)

    # Get session ID from page 2
    session_id2 = page2.locator('[data-testid="session-id"]').text_content(timeout=5000)

    # Sessions must have different IDs
    assert session_id1 != session_id2, \
        f"Two concurrent sessions have same ID: {session_id1}"

    # Both should show progress independently
    progress1 = page1.locator('[data-testid="conversion-progress"]')
    progress2 = page2.locator('[data-testid="conversion-progress"]')

    expect(progress1).to_be_visible(timeout=5000)
    expect(progress2).to_be_visible(timeout=5000)

    # Cleanup
    page1.close()
    page2.close()


@pytest.mark.critical
@pytest.mark.session
def test_session_survives_docker_restart(page: Page, test_ebook_txt: Path):
    """
    Test that sessions can resume after Docker container restart.

    PRODUCTION REQUIREMENT: For Docker deployments:
    - Sessions must be persisted to volume
    - Resume after container restart
    - Data integrity maintained
    - No corruption

    NOTE: This test requires Docker environment and may be skipped in CI.
    """
    # Check if running in Docker
    in_docker = Path("/.dockerenv").exists()

    if not in_docker:
        pytest.skip("Test requires Docker environment")

    # Start conversion
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    convert_button = page.locator('[data-testid="convert-button"]')
    convert_button.click(timeout=5000)

    # Wait for checkpoint
    time.sleep(5)

    session_id = page.locator('[data-testid="session-id"]').text_content(timeout=5000)

    # NOTE: Actual Docker restart would be done externally
    # This test documents the requirement

    # After restart, sessions should be loadable from /app/sessions
    # Test would verify session files exist and are valid JSON


@pytest.mark.session
def test_session_error_recovery(page: Page, test_ebook_txt: Path):
    """
    Test that sessions handle errors gracefully and can be retried.

    PRODUCTION REQUIREMENT: When errors occur:
    - Error message must be clear
    - Session state preserved
    - User can retry from checkpoint
    - Error logged for debugging
    """
    # This test would simulate various error conditions:
    # - Out of memory
    # - TTS model load failure
    # - Disk full
    # - Network timeout (for model downloads)

    # For now, document the requirement
    # Actual implementation would inject failures

    pass  # Placeholder for error injection tests
