"""
E2E Tests for Basic Ebook Conversion Flow

These tests verify the critical path: upload an ebook → configure settings → convert → download.

🔴 RED PHASE: These tests are written to expose production-readiness issues.
They expect proper:
- UI element IDs and data-testid attributes
- Clear error messages
- Progress indicators
- Proper state management
- Accessibility features
"""
import time
import pytest
from pathlib import Path
from playwright.sync_api import Page, expect


@pytest.mark.critical
@pytest.mark.smoke
@pytest.mark.conversion
@pytest.mark.ui
def test_application_loads_successfully(page: Page):
    """
    Test that the application loads and displays the main interface.

    PRODUCTION REQUIREMENT: Application must load within 5 seconds and show:
    - Title/header
    - File upload area
    - Configuration options
    - Convert button (disabled until file uploaded)
    """
    # Check page title
    expect(page).to_have_title("ebook2audiobook", timeout=5000)

    # Verify main container is visible
    gradio_container = page.locator(".gradio-container")
    expect(gradio_container).to_be_visible(timeout=5000)

    # Check for critical UI elements with data-testid
    # NOTE: This will FAIL if elements don't have proper test IDs
    file_upload = page.locator('[data-testid="ebook-file-upload"]')
    expect(file_upload).to_be_visible(timeout=3000)

    language_dropdown = page.locator('[data-testid="language-select"]')
    expect(language_dropdown).to_be_visible(timeout=3000)

    tts_engine_dropdown = page.locator('[data-testid="tts-engine-select"]')
    expect(tts_engine_dropdown).to_be_visible(timeout=3000)

    convert_button = page.locator('[data-testid="convert-button"]')
    expect(convert_button).to_be_visible(timeout=3000)

    # Convert button should be disabled initially
    expect(convert_button).to_be_disabled()


@pytest.mark.critical
@pytest.mark.conversion
@pytest.mark.ui
def test_file_upload_shows_filename(page: Page, test_ebook_txt: Path):
    """
    Test that uploading a file displays the filename correctly.

    PRODUCTION REQUIREMENT: User must see immediate feedback after upload:
    - Filename displayed
    - File size shown
    - Upload status clear
    """
    # Upload file
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    # Verify filename is displayed
    # This will FAIL if there's no clear filename display
    filename_display = page.locator('[data-testid="uploaded-filename"]')
    expect(filename_display).to_contain_text("test1.txt", timeout=5000)

    # Verify file size is shown
    filesize_display = page.locator('[data-testid="uploaded-filesize"]')
    expect(filesize_display).to_be_visible(timeout=3000)

    # Convert button should now be enabled
    convert_button = page.locator('[data-testid="convert-button"]')
    expect(convert_button).to_be_enabled(timeout=3000)


@pytest.mark.critical
@pytest.mark.conversion
@pytest.mark.ui
def test_language_selection_persists(page: Page, test_ebook_txt: Path):
    """
    Test that language selection is maintained and displayed correctly.

    PRODUCTION REQUIREMENT: Selected language must:
    - Be visible in dropdown
    - Persist during session
    - Be included in conversion job
    """
    # Upload file first
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    # Select language
    language_dropdown = page.locator('[data-testid="language-select"]')
    language_dropdown.click()

    # Select English
    english_option = page.locator('text="English (eng)"').or_(page.locator('[value="eng"]'))
    english_option.click(timeout=3000)

    # Verify selection persists
    expect(language_dropdown).to_contain_text("English", timeout=3000)

    # Refresh page and verify session persistence
    page.reload(wait_until="networkidle")

    # Language should still be selected (if session management works)
    language_dropdown = page.locator('[data-testid="language-select"]')
    # This may FAIL if session state is not preserved
    expect(language_dropdown).to_contain_text("English", timeout=3000)


@pytest.mark.critical
@pytest.mark.conversion
@pytest.mark.ui
def test_tts_engine_selection(page: Page, test_ebook_txt: Path):
    """
    Test TTS engine selection and display.

    PRODUCTION REQUIREMENT: TTS engine selection must:
    - Show all 6 available engines (XTTSv2, BARK, VITS, FAIRSEQ, TACOTRON2, YOURTTS)
    - Display engine capabilities
    - Persist selection
    """
    # Upload file
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    # Open TTS engine dropdown
    tts_dropdown = page.locator('[data-testid="tts-engine-select"]')
    tts_dropdown.click()

    # Verify all engines are available
    expected_engines = ["XTTSv2", "BARK", "VITS", "FAIRSEQ", "TACOTRON2", "YOURTTS"]

    for engine in expected_engines:
        engine_option = page.locator(f'text="{engine}"')
        expect(engine_option).to_be_visible(timeout=3000)

    # Select XTTSv2 (default/fastest)
    xtts_option = page.locator('text="XTTSv2"').first
    xtts_option.click()

    # Verify selection
    expect(tts_dropdown).to_contain_text("XTTSv2", timeout=3000)


@pytest.mark.critical
@pytest.mark.conversion
@pytest.mark.slow
def test_basic_conversion_complete_flow(
    page: Page,
    test_ebook_txt: Path,
    output_dir: Path
):
    """
    Test the complete conversion flow from upload to download.

    PRODUCTION REQUIREMENT: Basic conversion must:
    - Complete successfully for small files (<1min)
    - Show clear progress indicators
    - Provide downloadable output
    - Display success message
    - Not crash or hang

    This is the CRITICAL PATH test - it must pass for production.
    """
    # Step 1: Upload file
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    # Verify upload success
    expect(page.locator('[data-testid="uploaded-filename"]')).to_contain_text(
        "test1.txt", timeout=5000
    )

    # Step 2: Select language (English)
    language_dropdown = page.locator('[data-testid="language-select"]')
    language_dropdown.click()
    page.locator('text="English (eng)"').or_(page.locator('[value="eng"]')).first.click()

    # Step 3: Select TTS engine (XTTSv2 for speed)
    tts_dropdown = page.locator('[data-testid="tts-engine-select"]')
    tts_dropdown.click()
    page.locator('text="XTTSv2"').first.click()

    # Step 4: Click convert button
    convert_button = page.locator('[data-testid="convert-button"]')
    expect(convert_button).to_be_enabled(timeout=3000)
    convert_button.click()

    # Step 5: Verify progress indicator appears
    progress_indicator = page.locator('[data-testid="conversion-progress"]')
    expect(progress_indicator).to_be_visible(timeout=5000)

    # Step 6: Wait for conversion to complete
    # Progress should show percentage
    expect(progress_indicator).to_contain_text("%", timeout=10000)

    # Step 7: Wait for completion (max 60 seconds for small file)
    completion_message = page.locator('[data-testid="conversion-complete"]')
    expect(completion_message).to_be_visible(timeout=60000)

    # Step 8: Verify success message
    expect(completion_message).to_contain_text("Success", timeout=3000)
    expect(completion_message).to_contain_text("audiobook", timeout=3000)

    # Step 9: Verify download button is available
    download_button = page.locator('[data-testid="download-button"]')
    expect(download_button).to_be_visible(timeout=3000)
    expect(download_button).to_be_enabled()

    # Step 10: Verify download works
    with page.expect_download(timeout=10000) as download_info:
        download_button.click()

    download = download_info.value
    download_path = output_dir / download.suggested_filename
    download.save_as(download_path)

    # Verify downloaded file exists and has content
    assert download_path.exists(), "Downloaded file does not exist"
    assert download_path.stat().st_size > 0, "Downloaded file is empty"

    # Verify file extension is audio format
    assert download_path.suffix in [".mp3", ".m4b", ".wav", ".flac"], \
        f"Unexpected audio format: {download_path.suffix}"


@pytest.mark.critical
@pytest.mark.conversion
@pytest.mark.ui
def test_progress_updates_are_visible(page: Page, test_ebook_txt: Path):
    """
    Test that progress updates are visible and meaningful during conversion.

    PRODUCTION REQUIREMENT: Progress must:
    - Update in real-time
    - Show percentage (0-100%)
    - Show current step (e.g., "Extracting chapters", "Generating audio")
    - Not freeze or disappear
    """
    # Upload and start conversion
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    convert_button = page.locator('[data-testid="convert-button"]')
    convert_button.click(timeout=5000)

    # Verify progress appears
    progress_indicator = page.locator('[data-testid="conversion-progress"]')
    expect(progress_indicator).to_be_visible(timeout=5000)

    # Verify progress percentage element exists
    progress_percentage = page.locator('[data-testid="progress-percentage"]')
    expect(progress_percentage).to_be_visible(timeout=5000)

    # Verify progress message/step exists
    progress_message = page.locator('[data-testid="progress-message"]')
    expect(progress_message).to_be_visible(timeout=5000)

    # Progress percentage should update
    initial_progress = progress_percentage.text_content()
    time.sleep(5)
    updated_progress = progress_percentage.text_content()

    # This will FAIL if progress doesn't actually update
    assert initial_progress != updated_progress, \
        "Progress percentage did not update after 5 seconds"

    # Progress message should change through steps
    initial_message = progress_message.text_content()
    time.sleep(5)
    updated_message = progress_message.text_content()

    # May FAIL if no granular progress messages
    assert initial_message != updated_message or "100%" in updated_progress, \
        "Progress message did not update (conversion may be too fast or progress not granular)"


@pytest.mark.critical
@pytest.mark.conversion
@pytest.mark.ui
def test_cancel_conversion(page: Page, test_ebook_txt: Path):
    """
    Test that conversion can be cancelled mid-process.

    PRODUCTION REQUIREMENT: Cancel functionality must:
    - Be visible during conversion
    - Stop conversion immediately
    - Clean up resources
    - Return UI to ready state
    - Not leave zombie processes
    """
    # Upload and start conversion
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    convert_button = page.locator('[data-testid="convert-button"]')
    convert_button.click(timeout=5000)

    # Wait for conversion to start
    progress_indicator = page.locator('[data-testid="conversion-progress"]')
    expect(progress_indicator).to_be_visible(timeout=5000)

    # Verify cancel button is visible
    cancel_button = page.locator('[data-testid="cancel-button"]')
    expect(cancel_button).to_be_visible(timeout=3000)
    expect(cancel_button).to_be_enabled()

    # Click cancel
    cancel_button.click()

    # Verify cancellation confirmation
    cancel_confirmation = page.locator('[data-testid="cancel-confirmation"]')
    expect(cancel_confirmation).to_be_visible(timeout=5000)
    expect(cancel_confirmation).to_contain_text("cancelled", timeout=3000)

    # Verify UI returns to ready state
    convert_button = page.locator('[data-testid="convert-button"]')
    expect(convert_button).to_be_enabled(timeout=5000)

    # Progress indicator should be hidden
    expect(progress_indicator).not_to_be_visible(timeout=5000)


@pytest.mark.critical
@pytest.mark.ui
def test_ui_has_proper_accessibility(page: Page):
    """
    Test that UI has proper accessibility attributes for production.

    PRODUCTION REQUIREMENT: UI must have:
    - Proper ARIA labels
    - Keyboard navigation support
    - Screen reader compatibility
    - Focus indicators
    """
    # Check file upload has aria-label
    file_input = page.locator('input[type="file"]').first
    aria_label = file_input.get_attribute("aria-label")
    assert aria_label is not None and len(aria_label) > 0, \
        "File input missing aria-label"

    # Check convert button has proper label
    convert_button = page.locator('[data-testid="convert-button"]')
    button_text = convert_button.text_content()
    assert button_text and "convert" in button_text.lower(), \
        "Convert button has unclear label"

    # Test keyboard navigation
    page.keyboard.press("Tab")
    time.sleep(0.2)

    # Verify focus indicator is visible
    focused_element = page.evaluate("document.activeElement.tagName")
    assert focused_element, "No element received focus via Tab key"

    # Check for proper heading structure
    h1_count = page.locator("h1").count()
    assert h1_count > 0, "No H1 heading found (poor accessibility)"


@pytest.mark.critical
@pytest.mark.conversion
def test_output_format_selection(page: Page, test_ebook_txt: Path):
    """
    Test output format selection (MP3, M4B, WAV, FLAC).

    PRODUCTION REQUIREMENT: Output format must:
    - Be selectable before conversion
    - Be clearly displayed
    - Actually generate correct format
    - Include format info in filename
    """
    # Upload file
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    # Find output format selector
    format_selector = page.locator('[data-testid="output-format-select"]')
    expect(format_selector).to_be_visible(timeout=5000)

    # Open dropdown
    format_selector.click()

    # Verify all formats available
    expected_formats = ["MP3", "M4B", "WAV", "FLAC"]
    for fmt in expected_formats:
        format_option = page.locator(f'text="{fmt}"')
        expect(format_option).to_be_visible(timeout=3000)

    # Select M4B (best for audiobooks)
    page.locator('text="M4B"').click()

    # Verify selection
    expect(format_selector).to_contain_text("M4B", timeout=3000)


@pytest.mark.critical
@pytest.mark.conversion
def test_voice_selection_for_tts(page: Page, test_ebook_txt: Path):
    """
    Test voice selection for TTS engines.

    PRODUCTION REQUIREMENT: Voice selection must:
    - Show available voices for selected engine
    - Allow preview of voice samples
    - Persist voice choice
    - Use correct voice in conversion
    """
    # Upload file
    file_input = page.locator('input[type="file"]').first
    file_input.set_input_files(str(test_ebook_txt))

    # Select TTS engine that supports voices (XTTSv2)
    tts_dropdown = page.locator('[data-testid="tts-engine-select"]')
    tts_dropdown.click()
    page.locator('text="XTTSv2"').first.click()

    # Voice selector should appear
    voice_selector = page.locator('[data-testid="voice-select"]')
    expect(voice_selector).to_be_visible(timeout=5000)

    # Should show multiple voice options
    voice_selector.click()
    voice_options = page.locator('[role="option"]')
    assert voice_options.count() > 0, "No voice options available"

    # Select first voice
    voice_options.first.click()

    # Verify selection persists
    expect(voice_selector).not_to_be_empty(timeout=3000)
