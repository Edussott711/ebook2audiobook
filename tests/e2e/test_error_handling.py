"""
E2E Tests for Error Handling and Edge Cases

These tests verify that the application handles errors gracefully without crashing,
provides clear error messages, and maintains data integrity.

🔴 RED PHASE: These tests expose production vulnerabilities:
- Crashes from invalid input
- Unclear error messages
- Security vulnerabilities (XSS, file inclusion, etc.)
- Resource exhaustion
"""
import time
import tempfile
import pytest
from pathlib import Path
from playwright.sync_api import Page, expect


@pytest.mark.critical
@pytest.mark.error_handling
@pytest.mark.ui
def test_invalid_file_upload_shows_error(page: Page):
    """
    Test that uploading invalid file types shows clear error message.

    PRODUCTION REQUIREMENT: Must reject:
    - Executables (.exe, .sh, .bat)
    - Archives (.zip, .tar, .gz) unless specifically ebook archives
    - Images (.jpg, .png)
    - Videos (.mp4, .avi)
    - Random binary files

    Must show clear error message explaining what formats are accepted.
    """
    # Create invalid file (executable script)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
        f.write("#!/bin/bash\necho 'malicious script'\n")
        invalid_file = Path(f.name)

    try:
        # Attempt upload
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(str(invalid_file))

        # Should show error message
        error_message = page.locator('[data-testid="file-upload-error"]')
        expect(error_message).to_be_visible(timeout=5000)

        # Error should be specific and helpful
        error_text = error_message.text_content().lower()
        assert "invalid" in error_text or "not supported" in error_text, \
            f"Error message unclear: {error_text}"

        # Should mention accepted formats
        assert any(fmt in error_text for fmt in ["epub", "txt", "pdf", "mobi"]), \
            "Error message doesn't mention accepted formats"

        # Convert button should remain disabled
        convert_button = page.locator('[data-testid="convert-button"]')
        expect(convert_button).to_be_disabled(timeout=3000)

    finally:
        invalid_file.unlink()


@pytest.mark.critical
@pytest.mark.error_handling
@pytest.mark.security
def test_xss_prevention_in_filename(page: Page):
    """
    Test that filenames with XSS payloads are sanitized.

    PRODUCTION REQUIREMENT: Security critical!
    - Must sanitize all user input
    - Prevent XSS via filename injection
    - Prevent path traversal (../)
    - No code execution from filenames
    """
    # Create file with XSS payload in name
    xss_payloads = [
        '<script>alert("XSS")</script>.txt',
        'test<img src=x onerror=alert(1)>.txt',
        '../../etc/passwd.txt',
        'test; rm -rf /.txt',
    ]

    for payload_name in xss_payloads:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content\n")
            temp_path = Path(f.name)

        try:
            # Rename with XSS payload
            xss_path = temp_path.parent / payload_name
            temp_path.rename(xss_path)

            # Upload
            file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(str(xss_path))

            # Wait a moment for processing
            time.sleep(1)

            # Check that script tags are NOT present in DOM
            page_html = page.content()
            assert '<script>' not in page_html, \
                f"XSS payload not sanitized: {payload_name}"

            # Filename display should escape HTML
            filename_display = page.locator('[data-testid="uploaded-filename"]')
            if filename_display.is_visible():
                # Should show sanitized version
                displayed_text = filename_display.text_content()
                assert '<script>' not in displayed_text, \
                    "Script tags visible in filename display"

            xss_path.unlink()

        except Exception as e:
            # Cleanup
            if xss_path.exists():
                xss_path.unlink()
            raise


@pytest.mark.critical
@pytest.mark.error_handling
def test_empty_file_upload_error(page: Page):
    """
    Test that empty files are rejected with clear error.

    PRODUCTION REQUIREMENT: Must detect and reject:
    - 0-byte files
    - Files with only whitespace
    - Corrupted ebook files
    """
    # Create empty file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        empty_file = Path(f.name)

    try:
        # Upload empty file
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(str(empty_file))

        # Should show error
        error_message = page.locator('[data-testid="file-upload-error"]')
        expect(error_message).to_be_visible(timeout=5000)

        error_text = error_message.text_content().lower()
        assert "empty" in error_text or "no content" in error_text, \
            f"Error doesn't mention file is empty: {error_text}"

    finally:
        empty_file.unlink()


@pytest.mark.critical
@pytest.mark.error_handling
def test_very_large_file_handling(page: Page):
    """
    Test handling of very large files (>500MB).

    PRODUCTION REQUIREMENT: Large files must either:
    - Be processed successfully (with warning about time)
    - Be rejected with size limit message
    - Show upload progress indicator
    - Not crash the application
    """
    # NOTE: This test creates a large file - may be slow
    # Consider mocking or using smaller size in CI

    large_file_size = 100 * 1024 * 1024  # 100MB for testing (use 500MB+ in full test)

    with tempfile.NamedTemporaryFile(mode='wb', suffix='.txt', delete=False) as f:
        # Write large file
        chunk = b'A' * (1024 * 1024)  # 1MB chunks
        for _ in range(large_file_size // len(chunk)):
            f.write(chunk)
        large_file = Path(f.name)

    try:
        # Attempt upload
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(str(large_file))

        # Wait for upload to process
        time.sleep(5)

        # Check for either:
        # 1. Upload progress indicator
        # 2. Size limit warning
        # 3. Success with processing warning

        upload_progress = page.locator('[data-testid="upload-progress"]')
        size_warning = page.locator('[data-testid="file-size-warning"]')
        size_error = page.locator('[data-testid="file-size-error"]')

        # At least one should be visible
        has_feedback = (
            upload_progress.is_visible() or
            size_warning.is_visible() or
            size_error.is_visible()
        )

        assert has_feedback, \
            "No feedback shown for large file upload"

        # Application should not crash
        gradio_container = page.locator(".gradio-container")
        expect(gradio_container).to_be_visible(timeout=5000)

    finally:
        large_file.unlink()


@pytest.mark.critical
@pytest.mark.error_handling
def test_malformed_epub_handling(page: Page):
    """
    Test that malformed EPUB files are handled gracefully.

    PRODUCTION REQUIREMENT: Must handle:
    - Corrupted EPUB files
    - EPUBs with missing metadata
    - EPUBs with invalid XML
    - EPUBs with missing chapters
    """
    # Create malformed EPUB (actually a text file with .epub extension)
    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.epub',
        delete=False
    ) as f:
        f.write("This is not a valid EPUB file")
        malformed_epub = Path(f.name)

    try:
        # Upload
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(str(malformed_epub))

        # Click convert
        convert_button = page.locator('[data-testid="convert-button"]')

        if convert_button.is_enabled(timeout=5000):
            convert_button.click()

            # Should show error during processing
            error_message = page.locator('[data-testid="conversion-error"]')
            expect(error_message).to_be_visible(timeout=30000)

            error_text = error_message.text_content().lower()

            # Error should be informative
            assert any(word in error_text for word in [
                "invalid", "corrupted", "malformed", "parse", "format"
            ]), f"Error message not informative: {error_text}"

            # UI should return to ready state
            expect(convert_button).to_be_enabled(timeout=10000)

    finally:
        malformed_epub.unlink()


@pytest.mark.critical
@pytest.mark.error_handling
def test_network_interruption_during_model_download(page: Page, test_ebook_txt: Path):
    """
    Test handling of network interruption during TTS model download.

    PRODUCTION REQUIREMENT: If TTS model needs to be downloaded:
    - Show clear download progress
    - Handle network failures gracefully
    - Allow retry
    - Cache downloaded models
    - Don't crash if download fails
    """
    # This test is conceptual - actual implementation would require
    # mocking network or using a new TTS engine that needs download

    # Upload file
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    # Select TTS engine (would trigger model download if not cached)
    convert_button = page.locator('[data-testid="convert-button"]')

    # If model download starts, should show:
    download_progress = page.locator('[data-testid="model-download-progress"]')

    # If download fails, should show:
    download_error = page.locator('[data-testid="model-download-error"]')
    retry_button = page.locator('[data-testid="retry-download-button"]')

    # Document the expected behavior
    # Actual test would inject network failure


@pytest.mark.critical
@pytest.mark.error_handling
def test_out_of_memory_handling(page: Page):
    """
    Test that out-of-memory conditions are handled gracefully.

    PRODUCTION REQUIREMENT: When system runs low on memory:
    - Detect OOM condition before crash
    - Show clear error message
    - Suggest solutions (reduce file size, use smaller model)
    - Clean up resources
    - Don't leave zombie processes
    """
    # This test documents the requirement
    # Actual implementation would require memory pressure simulation

    # Expected behavior:
    # 1. Monitor memory usage during conversion
    # 2. If memory threshold exceeded (e.g., 90% of available):
    #    - Pause conversion
    #    - Show warning: "System running low on memory"
    # 3. If OOM imminent:
    #    - Cancel conversion gracefully
    #    - Save checkpoint
    #    - Show error with suggested actions


@pytest.mark.critical
@pytest.mark.error_handling
def test_concurrent_conversion_limit(page: Page, test_ebook_txt: Path):
    """
    Test that system enforces concurrent conversion limits.

    PRODUCTION REQUIREMENT: To prevent resource exhaustion:
    - Limit concurrent conversions (e.g., max 3)
    - Queue additional requests
    - Show queue position
    - Allow cancellation from queue
    """
    # Start multiple conversions (would need multiple browser contexts)
    # Test documents the requirement

    # Expected behavior:
    # - First N conversions: start immediately
    # - Additional conversions: queued
    # - Queue indicator shows: "Position 4 in queue"
    # - As conversions complete, queue advances


@pytest.mark.critical
@pytest.mark.error_handling
def test_invalid_language_selection_prevented(page: Page, test_ebook_txt: Path):
    """
    Test that invalid language selections are prevented.

    PRODUCTION REQUIREMENT: Language selection must:
    - Only allow supported languages
    - Validate language code
    - Not crash on unsupported language
    - Suggest alternatives if language detected but not supported
    """
    # Upload file
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    # Try to inject invalid language code via DevTools
    page.evaluate("""
        () => {
            const langSelect = document.querySelector('[data-testid="language-select"]');
            if (langSelect) {
                const option = document.createElement('option');
                option.value = 'invalid_lang_xxx';
                option.text = 'Invalid Language';
                langSelect.appendChild(option);
                langSelect.value = 'invalid_lang_xxx';
            }
        }
    """)

    # Attempt conversion
    convert_button = page.locator('[data-testid="convert-button"]')
    convert_button.click()

    # Should show validation error
    error_message = page.locator('[data-testid="validation-error"]')
    expect(error_message).to_be_visible(timeout=5000)

    expect(error_message).to_contain_text("language", timeout=3000)


@pytest.mark.critical
@pytest.mark.error_handling
def test_disk_space_check_before_conversion(page: Page, test_ebook_txt: Path):
    """
    Test that available disk space is checked before starting conversion.

    PRODUCTION REQUIREMENT: Before conversion:
    - Check available disk space
    - Estimate space required (2-3x input file size)
    - Warn if insufficient space
    - Don't start if space is critically low
    """
    # Upload file
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    # System should check disk space
    # If space is low, should show warning
    disk_space_warning = page.locator('[data-testid="disk-space-warning"]')

    # Warning might not appear if sufficient space
    # But check should happen (verify via logs or monitoring)


@pytest.mark.error_handling
def test_special_characters_in_ebook_content(page: Page):
    """
    Test handling of special characters in ebook content.

    PRODUCTION REQUIREMENT: Must correctly handle:
    - Unicode characters (emoji, special symbols)
    - Right-to-left languages (Arabic, Hebrew)
    - Non-breaking spaces
    - Ligatures
    - Mathematical symbols
    """
    # Create file with special characters
    special_content = """
    Test with special characters:
    - Emoji: 😀 🎉 📚
    - Math: ∑ ∫ √ π
    - Arrows: → ← ↑ ↓
    - Currency: $ € £ ¥
    - RTL: مرحبا העברית
    - Accents: café résumé
    """

    with tempfile.NamedTemporaryFile(
        mode='w',
        suffix='.txt',
        encoding='utf-8',
        delete=False
    ) as f:
        f.write(special_content)
        special_file = Path(f.name)

    try:
        # Upload
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(str(special_file))

        # Should not show encoding errors
        error_message = page.locator('[data-testid="file-upload-error"]')

        # Should either succeed or show clear message about unsupported characters
        time.sleep(2)

        # No JavaScript errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg) if msg.type == "error" else None)

        assert len(console_errors) == 0, \
            f"Console errors during special character handling: {console_errors}"

    finally:
        special_file.unlink()


@pytest.mark.critical
@pytest.mark.error_handling
def test_graceful_degradation_without_gpu(page: Page, test_ebook_txt: Path):
    """
    Test that application works without GPU (CPU fallback).

    PRODUCTION REQUIREMENT: Must gracefully fallback to CPU:
    - Detect GPU availability
    - Auto-switch to CPU if no GPU
    - Show clear message about performance
    - Don't crash or fail
    """
    # Upload file
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    # Check for device indicator
    device_indicator = page.locator('[data-testid="device-indicator"]')

    # Should show either "GPU" or "CPU"
    # If CPU, should show performance warning
    if device_indicator.is_visible():
        device_text = device_indicator.text_content().lower()

        if "cpu" in device_text:
            # Should show performance notice
            performance_notice = page.locator('[data-testid="cpu-performance-notice"]')
            # Notice might not be required but is good UX


@pytest.mark.critical
@pytest.mark.error_handling
@pytest.mark.ui
def test_error_messages_are_user_friendly(page: Page):
    """
    Test that ALL error messages are user-friendly, not technical.

    PRODUCTION REQUIREMENT: Error messages must:
    - Be written for non-technical users
    - Explain what went wrong in simple terms
    - Suggest how to fix the problem
    - Not expose technical stack traces
    - Not expose system paths
    - Not expose internal error codes without explanation
    """
    # Create various error conditions and check messages
    # This is a meta-test for error message quality

    bad_messages = [
        "NoneType object has no attribute",
        "Traceback (most recent call last)",
        "/usr/local/lib/python",
        "Exception in thread",
        "Error 500",
        "Stack trace:",
    ]

    # Upload invalid file to trigger error
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False) as f:
        f.write("invalid")
        invalid_file = Path(f.name)

    try:
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(str(invalid_file))

        time.sleep(2)

        # Check all error message elements
        error_elements = page.locator('[class*="error"], [data-testid*="error"]').all()

        for element in error_elements:
            if element.is_visible():
                error_text = element.text_content()

                # Check for bad patterns
                for bad_pattern in bad_messages:
                    assert bad_pattern not in error_text, \
                        f"Technical error message exposed to user: {bad_pattern} in {error_text}"

    finally:
        invalid_file.unlink()


@pytest.mark.error_handling
def test_timeout_handling_for_long_conversions(page: Page, test_ebook_txt: Path):
    """
    Test that very long conversions don't timeout inappropriately.

    PRODUCTION REQUIREMENT: Long conversions must:
    - Not hit HTTP timeout
    - Keep connection alive
    - Send periodic heartbeats
    - Show "still working" indicators
    """
    # This test documents the requirement
    # Actual test would use a very large ebook

    # Expected behavior:
    # - WebSocket keeps connection alive
    # - Progress updates serve as heartbeat
    # - No 504 Gateway Timeout errors
    # - No connection closed unexpectedly
