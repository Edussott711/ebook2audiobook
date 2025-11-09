# 🎯 Production Readiness Checklist

This document lists issues exposed by the e2e tests that must be addressed for production deployment.

**Status**: 🔴 RED PHASE - Issues identified, fixes pending

## 🔴 Critical Issues (Blocking Production)

### 1. Missing UI Test Identifiers

**Problem**: Gradio components lack `data-testid` attributes, making automated testing impossible.

**Impact**:
- Cannot verify UI functionality automatically
- Difficult to debug issues in production
- Poor maintainability

**Fix Required**:
Add `elem_id` parameter to all Gradio components in `lib/functions.py`:

```python
# Before:
ebook_file = gr.File(label="Upload Ebook")

# After:
ebook_file = gr.File(
    label="Upload Ebook",
    elem_id="ebook-file-upload"
)
```

**Components needing IDs**:
- `ebook-file-upload` - File upload component
- `language-select` - Language dropdown
- `tts-engine-select` - TTS engine dropdown
- `voice-select` - Voice selection dropdown
- `output-format-select` - Output format dropdown
- `convert-button` - Convert button
- `cancel-button` - Cancel button (if exists)
- `conversion-progress` - Progress indicator
- `progress-percentage` - Progress percentage display
- `progress-message` - Progress message/step
- `conversion-complete` - Completion message
- `conversion-error` - Error message display
- `download-button` - Download button
- `session-id` - Session ID display (for debugging)
- `uploaded-filename` - Uploaded file name display
- `uploaded-filesize` - File size display

**Affected Tests**: Nearly all tests
**Priority**: 🔴 CRITICAL

---

### 2. Session Management UI Missing

**Problem**: No UI for viewing, resuming, or managing conversion sessions.

**Impact**:
- Users can't see their active conversions
- Can't resume after browser refresh
- No visibility into conversion history

**Fix Required**:
Implement session management UI:

1. **Sessions Tab/Panel**:
   ```python
   with gr.Tab("Sessions", elem_id="sessions-tab"):
       session_list = gr.DataFrame(
           headers=["Status", "Ebook", "Progress", "Started", "Actions"],
           elem_id="session-list"
       )
       refresh_btn = gr.Button("Refresh", elem_id="refresh-sessions")
   ```

2. **Resume Dialog**:
   ```python
   resume_dialog = gr.Modal(visible=False, elem_id="resume-dialog")
   with resume_dialog:
       gr.Markdown("### Resume Previous Session?")
       gr.Markdown(elem_id="resume-info")
       with gr.Row():
           resume_btn = gr.Button("Resume", elem_id="resume-button")
           start_new_btn = gr.Button("Start New")
   ```

3. **Backend Functions**:
   - `list_active_sessions()` - Get all sessions
   - `resume_session(session_id)` - Resume from checkpoint
   - `delete_session(session_id)` - Clean up session
   - `auto_reconnect()` - Detect and reconnect on page load

**Affected Tests**:
- `test_session_persists_after_browser_refresh`
- `test_session_list_shows_active_conversions`
- `test_resume_session_from_checkpoint`

**Priority**: 🔴 CRITICAL

---

### 3. No Cancel Functionality

**Problem**: Users cannot cancel in-progress conversions.

**Impact**:
- Stuck conversions block resources
- No way to stop long-running jobs
- Poor user experience

**Fix Required**:

1. **Add cancel button**:
   ```python
   cancel_btn = gr.Button(
       "Cancel",
       visible=False,
       elem_id="cancel-button"
   )
   ```

2. **Implement cancellation logic**:
   ```python
   def cancel_conversion(session_id):
       # Set cancellation flag
       session_context.set_cancel_flag(session_id)

       # Terminate processes
       terminate_session_processes(session_id)

       # Clean up temp files
       cleanup_session_files(session_id)

       return "Conversion cancelled"
   ```

3. **Check cancel flag during conversion**:
   ```python
   for sentence in sentences:
       if session_context.is_cancelled(session_id):
           raise ConversionCancelled("User cancelled")
       # ... generate audio
   ```

**Affected Tests**:
- `test_cancel_conversion`

**Priority**: 🔴 CRITICAL

---

### 4. Unclear Error Messages

**Problem**: Technical errors exposed directly to users.

**Impact**:
- Confusing user experience
- Security risk (exposes internal paths)
- Poor professionalism

**Fix Required**:

Wrap all exceptions with user-friendly messages:

```python
# lib/functions.py

USER_FRIENDLY_ERRORS = {
    "FileNotFoundError": "The file could not be found. Please try uploading again.",
    "PermissionError": "Permission denied. Please check file access rights.",
    "MemoryError": "Not enough memory to process this file. Try a smaller file or use a more powerful machine.",
    "ebooklib.EPUBException": "This EPUB file appears to be corrupted or invalid. Please try a different file.",
}

def convert_ebook(*args, **kwargs):
    try:
        # ... conversion logic
    except Exception as e:
        error_type = type(e).__name__
        user_message = USER_FRIENDLY_ERRORS.get(
            error_type,
            "An unexpected error occurred. Please try again or contact support."
        )

        # Log technical details for debugging
        logger.error(f"Conversion failed: {error_type}: {str(e)}", exc_info=True)

        # Show user-friendly message
        return None, user_message
```

**Affected Tests**:
- `test_error_messages_are_user_friendly`
- All error handling tests

**Priority**: 🔴 CRITICAL

---

### 5. Missing Input Validation

**Problem**: No validation of user inputs before processing.

**Impact**:
- Security vulnerabilities (XSS, path traversal)
- Application crashes from invalid data
- Resource exhaustion

**Fix Required**:

1. **File validation**:
   ```python
   def validate_ebook_file(file):
       # Check file size
       max_size = 500 * 1024 * 1024  # 500MB
       if file.size > max_size:
           raise ValueError(f"File too large. Maximum size is 500MB.")

       # Check file extension
       allowed_extensions = ['.epub', '.txt', '.pdf', '.mobi']
       if not any(file.name.endswith(ext) for ext in allowed_extensions):
           raise ValueError(f"Unsupported format. Use: {', '.join(allowed_extensions)}")

       # Check if file is empty
       if file.size == 0:
           raise ValueError("File is empty. Please upload a valid ebook.")

       # Sanitize filename (prevent XSS and path traversal)
       safe_filename = sanitize_filename(file.name)

       return safe_filename
   ```

2. **Filename sanitization**:
   ```python
   import re
   from pathlib import Path

   def sanitize_filename(filename):
       # Remove any path components
       filename = Path(filename).name

       # Remove or escape HTML/script tags
       filename = re.sub(r'<[^>]*>', '', filename)

       # Remove potentially dangerous characters
       filename = re.sub(r'[^\w\s\-\.]', '_', filename)

       # Limit length
       if len(filename) > 255:
           name, ext = os.path.splitext(filename)
           filename = name[:250] + ext

       return filename
   ```

3. **Language code validation**:
   ```python
   def validate_language(lang_code):
       from iso639 import languages

       try:
           languages.get(part3=lang_code)
           return True
       except KeyError:
           raise ValueError(f"Invalid language code: {lang_code}")
   ```

**Affected Tests**:
- `test_xss_prevention_in_filename`
- `test_invalid_file_upload_shows_error`
- `test_empty_file_upload_error`
- `test_invalid_language_selection_prevented`

**Priority**: 🔴 CRITICAL (Security)

---

### 6. No Progress Granularity

**Problem**: Progress updates are too coarse or non-existent.

**Impact**:
- Users don't know if conversion is stuck
- Poor user experience for long conversions
- Appears frozen

**Fix Required**:

1. **Add detailed progress tracking**:
   ```python
   def convert_with_progress(ebook_file, session_id):
       stages = [
           ("Converting to EPUB", 10),
           ("Extracting chapters", 20),
           ("Tokenizing text", 30),
           ("Generating audio", 80),  # Most time here
           ("Combining audio files", 95),
           ("Creating final audiobook", 100),
       ]

       for stage_name, stage_pct in stages:
           update_progress(session_id, stage_pct, stage_name)
           # ... do work
   ```

2. **Real-time sentence progress**:
   ```python
   total_sentences = len(all_sentences)

   for idx, sentence in enumerate(all_sentences):
       # Calculate progress within audio generation stage (30% to 80%)
       sentence_progress = 30 + (50 * idx / total_sentences)

       update_progress(
           session_id,
           sentence_progress,
           f"Generating audio: {idx}/{total_sentences} sentences"
       )
   ```

3. **WebSocket for real-time updates**:
   ```python
   # Use Gradio's built-in streaming
   def convert_ebook_streaming(...):
       for progress_update in conversion_generator():
           yield progress_update
   ```

**Affected Tests**:
- `test_progress_updates_are_visible`
- `test_basic_conversion_complete_flow`

**Priority**: 🔴 CRITICAL

---

## 🟡 High Priority Issues (Important but not blocking)

### 7. No Disk Space Check

**Problem**: No pre-flight check for available disk space.

**Impact**:
- Conversions fail mid-process
- Corrupted output files
- Poor user experience

**Fix Required**:
```python
import shutil

def check_disk_space(required_bytes):
    stat = shutil.disk_usage("/")
    available = stat.free

    if available < required_bytes:
        raise InsufficientDiskSpaceError(
            f"Not enough disk space. Need {required_bytes / (1024**3):.1f}GB, "
            f"have {available / (1024**3):.1f}GB available."
        )

    # Warn if close to limit
    if available < required_bytes * 1.5:
        return {
            "warning": True,
            "message": "Disk space is running low. Conversion may fail."
        }

    return {"warning": False}
```

**Priority**: 🟡 HIGH

---

### 8. No Concurrent Conversion Limits

**Problem**: Unlimited concurrent conversions can exhaust resources.

**Impact**:
- Server overload
- OOM crashes
- Poor performance for all users

**Fix Required**:
```python
from queue import Queue
import threading

class ConversionQueue:
    def __init__(self, max_concurrent=3):
        self.max_concurrent = max_concurrent
        self.active_conversions = 0
        self.queue = Queue()
        self.lock = threading.Lock()

    def can_start(self):
        with self.lock:
            return self.active_conversions < self.max_concurrent

    def start_conversion(self, session_id):
        with self.lock:
            if self.can_start():
                self.active_conversions += 1
                return True
            else:
                self.queue.put(session_id)
                return False

    def finish_conversion(self, session_id):
        with self.lock:
            self.active_conversions -= 1

            # Start next in queue
            if not self.queue.empty():
                next_session = self.queue.get()
                self.start_conversion(next_session)
```

**Priority**: 🟡 HIGH

---

### 9. No Accessibility Attributes

**Problem**: Missing ARIA labels and keyboard navigation support.

**Impact**:
- Unusable for screen reader users
- Poor accessibility score
- Legal compliance issues (ADA, WCAG)

**Fix Required**:
```python
# Add aria-label to all interactive elements
file_upload = gr.File(
    label="Upload Ebook",
    elem_id="ebook-file-upload",
    aria_label="Upload ebook file in EPUB, PDF, TXT, or MOBI format"
)

# Add keyboard shortcuts
gr.Markdown("""
### Keyboard Shortcuts
- `Ctrl+U` or `Cmd+U`: Upload file
- `Ctrl+Enter` or `Cmd+Enter`: Start conversion
- `Esc`: Cancel conversion
""")
```

**Priority**: 🟡 HIGH

---

## 🟢 Medium Priority Issues (Should fix)

### 10. No Model Download Progress

**Problem**: When TTS models are downloaded, no progress is shown.

**Impact**:
- Appears frozen during first-time setup
- Users may close browser thinking it's stuck

**Fix**: Show download progress with file size and speed.

---

### 11. No Session Cleanup

**Problem**: Old sessions accumulate on disk.

**Impact**:
- Disk space exhaustion over time
- Performance degradation

**Fix**: Implement automatic cleanup job (already partially implemented in `session_persistence.py`, needs UI integration).

---

### 12. No Batch Conversion UI

**Problem**: Batch conversion only available via CLI.

**Impact**:
- Limited usability
- Users upload files one at a time

**Fix**: Add multi-file upload with batch progress tracking.

---

## 📊 Testing Progress

### Tests Written
- ✅ Basic conversion flow (11 tests)
- ✅ Session persistence (8 tests)
- ✅ Error handling (14 tests)
- **Total: 33 tests**

### Tests Passing
- 🔴 0 / 33 (Expected - RED phase)

### Phase Status
- 🔴 **RED Phase**: Complete - Issues identified
- ⏳ **GREEN Phase**: Pending - Fixes needed
- ⏳ **REFACTOR Phase**: Not started

---

## 🚀 Implementation Order

Recommended order to fix issues:

1. **Phase 1 - Basic Functionality** (1-2 days)
   - [ ] Add `elem_id` to all UI components (#1)
   - [ ] Add progress granularity (#6)
   - [ ] Implement input validation (#5)

2. **Phase 2 - Session Management** (2-3 days)
   - [ ] Build session management UI (#2)
   - [ ] Implement cancel functionality (#3)
   - [ ] Add session resume logic (#2)

3. **Phase 3 - Error Handling** (1-2 days)
   - [ ] Wrap all errors with user-friendly messages (#4)
   - [ ] Add disk space checks (#7)
   - [ ] Implement resource limits (#8)

4. **Phase 4 - Polish** (1-2 days)
   - [ ] Add accessibility attributes (#9)
   - [ ] Implement model download progress (#10)
   - [ ] Add session cleanup (#11)

**Estimated Total**: 5-9 days of development

---

## 📈 Success Metrics

When GREEN phase is complete:

- ✅ All critical tests passing
- ✅ Zero security vulnerabilities
- ✅ All user inputs validated
- ✅ Error messages user-friendly
- ✅ Session management working
- ✅ Progress updates smooth
- ✅ No resource exhaustion possible

**Then ready for production! 🚀**
