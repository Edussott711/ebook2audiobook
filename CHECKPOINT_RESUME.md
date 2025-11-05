# 💾 Checkpoint & Resume Feature

## Overview

The ebook2audiobook converter now includes an automatic checkpoint and resume system that allows you to:
- **Stop a conversion at any time** and resume later from where you left off
- **Recover from crashes or interruptions** automatically
- **Save time** by not having to restart long conversions from scratch

## How It Works

### Automatic Checkpoints

The system automatically saves your progress at key stages:

1. **After EPUB Conversion** - Once your ebook is converted to EPUB format
2. **After Chapter Extraction** - When chapters and text have been parsed
3. **During Audio Conversion** - As each chapter's audio is generated
4. **At Completion** - When the final audiobook is created

Checkpoints are saved as `checkpoint.json` files in your session's processing directory and contain:
- Session configuration (TTS engine, voice settings, language, etc.)
- Current conversion stage
- Metadata and cover information
- Timestamp of last save

### Resume Behavior

When you restart a conversion with the same session ID:

```bash
# Initial conversion (gets interrupted)
./ebook2audiobook.sh --headless --ebook "my_book.epub" --language en --session my-session-123

# Resume from checkpoint
./ebook2audiobook.sh --headless --ebook "my_book.epub" --language en --session my-session-123
```

The system will:
1. ✓ Detect the existing checkpoint
2. ✓ Restore your session configuration
3. ✓ Skip already-completed stages
4. ✓ Resume from the last successful checkpoint
5. ✓ Continue converting from where it stopped

### What Gets Preserved

When resuming from a checkpoint:

- ✓ **Audio files** - All generated sentence and chapter audio files
- ✓ **Session settings** - TTS engine, voice, temperature, and other parameters
- ✓ **Metadata** - Book title, author, cover image
- ✓ **EPUB file** - Converted and parsed book content
- ✓ **Progress state** - Exactly which stage you were at

### What Doesn't Need Re-conversion

The intelligent resume system skips:
- Already-converted audio sentences
- Already-combined chapter audio files
- Already-extracted metadata and cover
- Already-converted EPUB files

This means you only redo work that wasn't completed!

## Usage Examples

### Basic Resume (CLI)

```bash
# Start conversion with a session ID
./ebook2audiobook.sh --headless \
  --ebook "long_book.epub" \
  --language en \
  --session my-book-session

# If interrupted, resume with the SAME session ID
./ebook2audiobook.sh --headless \
  --ebook "long_book.epub" \
  --language en \
  --session my-book-session
```

### Force Restart from Beginning

If you want to ignore the checkpoint and start fresh:

```bash
./ebook2audiobook.sh --headless \
  --ebook "long_book.epub" \
  --language en \
  --session my-book-session \
  --force_restart
```

This will delete the existing checkpoint and restart the entire conversion.

### GUI Mode

The checkpoint system also works in GUI mode:
1. Start your conversion in the web interface
2. If interrupted, simply restart the application
3. Use the same session ID if you want to resume
4. The system will automatically detect and load the checkpoint

## Checkpoint Stages

The system uses these stage identifiers:

| Stage | Description |
|-------|-------------|
| `epub_converted` | EPUB file has been created and is ready |
| `chapters_extracted` | Chapters have been parsed and sentences prepared |
| `audio_converted` | All audio files have been generated |
| `completed` | Final audiobook has been assembled |

## Technical Details

### Checkpoint File Location

Checkpoints are stored at:
```
tmp/proc-{session-id}/{ebook-hash}/checkpoint.json
```

### Checkpoint File Format

Example checkpoint:
```json
{
  "version": "1.0",
  "timestamp": "2025-11-05T14:30:45.123456",
  "stage": "audio_converted",
  "session_id": "my-session-123",
  "ebook": "/path/to/book.epub",
  "epub_path": "/tmp/proc-my-session-123/abc123/__book.epub",
  "tts_engine": "xtts",
  "language": "eng",
  "voice": "/path/to/voice.wav",
  "metadata": {
    "title": "My Book",
    "creator": "Author Name",
    ...
  },
  "chapters_count": 25
}
```

### Checkpoint Cleanup

Checkpoints are automatically deleted when:
- ✓ Conversion completes successfully
- ✓ You use `--force_restart` flag

Checkpoints are preserved when:
- ✗ Conversion is interrupted (Ctrl+C, crash, etc.)
- ✗ An error occurs during processing
- ✗ User cancels the conversion

## Troubleshooting

### "No checkpoint found" when you expect one

**Possible causes:**
- Different session ID was used
- Checkpoint file was manually deleted
- Process directory was cleaned up

**Solution:** Start a new conversion or check your session ID

### Checkpoint loads but conversion fails

**Possible causes:**
- Source file was modified or moved
- Audio files were manually deleted
- Corrupted checkpoint file

**Solution:** Use `--force_restart` to start fresh

### Want to start over despite checkpoint

**Solution:** Use the `--force_restart` flag:
```bash
./ebook2audiobook.sh --headless \
  --ebook "book.epub" \
  --language en \
  --session my-session \
  --force_restart
```

## Benefits

### Time Savings
For a 500-page book that takes 2 hours to convert:
- Without checkpoints: Must restart all 2 hours if interrupted
- With checkpoints: Resume from the last stage (might be 95% done!)

### Reliability
- No fear of losing progress due to power outages
- Safe to stop conversions when needed
- Automatic recovery from crashes

### Flexibility
- Pause long conversions to free up GPU/CPU
- Split work across multiple sessions
- Test different settings without losing base progress

## Best Practices

1. **Use consistent session IDs** - Pick a memorable ID for each book
2. **Keep source files in place** - Don't move or rename your ebook during conversion
3. **Monitor disk space** - Checkpoints and audio files require storage
4. **Clean up when done** - Old session directories can be safely deleted after completion

## FAQ

**Q: Does this work with batch conversions?**
A: Yes! Each book in a batch gets its own checkpoint.

**Q: Can I resume on a different computer?**
A: Not directly - checkpoints include local file paths. You'd need to transfer the entire session directory.

**Q: How much space do checkpoints use?**
A: Minimal - typically 1-5 KB per checkpoint. The audio files take much more space.

**Q: Will checkpoints work if I upgrade the software?**
A: Checkpoints include a version number. Incompatible versions will be ignored.

**Q: Can I manually edit checkpoint files?**
A: Not recommended - the JSON format is for the system to read. Use CLI flags instead.

---

**Feature added:** November 2025
**Checkpoint Version:** 1.0
