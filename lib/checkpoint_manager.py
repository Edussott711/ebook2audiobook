"""
Checkpoint Manager Module
Handles saving and restoring ebook conversion progress to enable resume functionality.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional


class CheckpointManager:
    """Manages checkpoint creation and restoration for ebook conversion sessions."""

    CHECKPOINT_FILE = "checkpoint.json"
    CHECKPOINT_VERSION = "1.0"

    def __init__(self, session: Dict[str, Any]):
        """
        Initialize checkpoint manager for a session.

        Args:
            session: The session context dictionary
        """
        self.session = session
        self.checkpoint_path = self._get_checkpoint_path()

    def _get_checkpoint_path(self) -> Optional[str]:
        """Get the path to the checkpoint file for this session."""
        if not self.session.get('process_dir'):
            return None
        return os.path.join(self.session['process_dir'], self.CHECKPOINT_FILE)

    def save_checkpoint(self, stage: str, additional_data: Optional[Dict] = None) -> bool:
        """
        Save a checkpoint of the current session state.

        Args:
            stage: The current stage of conversion (e.g., 'epub_converted', 'chapters_extracted',
                   'audio_conversion', 'chapters_combined', 'completed')
            additional_data: Optional additional data to save with checkpoint

        Returns:
            bool: True if checkpoint was saved successfully, False otherwise
        """
        try:
            if not self.checkpoint_path:
                return False

            # Extract serializable data from session
            checkpoint_data = {
                "version": self.CHECKPOINT_VERSION,
                "timestamp": datetime.now().isoformat(),
                "stage": stage,
                "session_id": self.session.get('id'),
                "ebook": self.session.get('ebook'),
                "epub_path": self.session.get('epub_path'),
                "filename_noext": self.session.get('filename_noext'),
                "language": self.session.get('language'),
                "language_iso1": self.session.get('language_iso1'),
                "tts_engine": self.session.get('tts_engine'),
                "voice": self.session.get('voice'),
                "custom_model": self.session.get('custom_model'),
                "temperature": self.session.get('temperature'),
                "length_penalty": self.session.get('length_penalty'),
                "num_beams": self.session.get('num_beams'),
                "repetition_penalty": self.session.get('repetition_penalty'),
                "top_k": self.session.get('top_k'),
                "top_p": self.session.get('top_p'),
                "speed": self.session.get('speed'),
                "enable_text_splitting": self.session.get('enable_text_splitting'),
                "text_temp": self.session.get('text_temp'),
                "waveform_temp": self.session.get('waveform_temp'),
                "output_format": self.session.get('output_format'),
                "output_split": self.session.get('output_split'),
                "output_split_hours": self.session.get('output_split_hours'),
                "fine_tuned": self.session.get('fine_tuned'),
                "device": self.session.get('device'),
                "metadata": self._serialize_dict(self.session.get('metadata', {})),
                "toc": self.session.get('toc'),
                "cover": self.session.get('cover'),
                "chapters_dir": self.session.get('chapters_dir'),
                "chapters_dir_sentences": self.session.get('chapters_dir_sentences'),
                "audiobooks_dir": self.session.get('audiobooks_dir'),
                "final_name": self.session.get('final_name'),
                "audiobook": self.session.get('audiobook'),
            }

            # Add chapter information if available
            if self.session.get('chapters'):
                checkpoint_data['chapters_count'] = len(self.session['chapters'])
                # Store chapter sentence counts for verification
                checkpoint_data['chapters_sentences'] = [
                    len(chapter) for chapter in self.session['chapters']
                ]

            # Add any additional data
            if additional_data:
                checkpoint_data['additional'] = additional_data

            # Save to file
            with open(self.checkpoint_path, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2, ensure_ascii=False)

            print(f"✓ Checkpoint saved: {stage}")
            return True

        except Exception as e:
            print(f"Warning: Failed to save checkpoint: {e}")
            return False

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint data from file.

        Returns:
            Optional[Dict]: Checkpoint data if found and valid, None otherwise
        """
        try:
            if not self.checkpoint_path or not os.path.exists(self.checkpoint_path):
                return None

            with open(self.checkpoint_path, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)

            # Validate checkpoint version
            if checkpoint_data.get('version') != self.CHECKPOINT_VERSION:
                print(f"Warning: Checkpoint version mismatch. Expected {self.CHECKPOINT_VERSION}, "
                      f"found {checkpoint_data.get('version')}")
                return None

            return checkpoint_data

        except Exception as e:
            print(f"Warning: Failed to load checkpoint: {e}")
            return None

    def restore_from_checkpoint(self) -> bool:
        """
        Restore session state from checkpoint.

        Returns:
            bool: True if restoration was successful, False otherwise
        """
        try:
            checkpoint_data = self.load_checkpoint()
            if not checkpoint_data:
                return False

            # Restore session fields
            restore_fields = [
                'epub_path', 'filename_noext', 'language', 'language_iso1',
                'tts_engine', 'voice', 'custom_model', 'temperature', 'length_penalty',
                'num_beams', 'repetition_penalty', 'top_k', 'top_p', 'speed',
                'enable_text_splitting', 'text_temp', 'waveform_temp',
                'output_format', 'output_split', 'output_split_hours',
                'fine_tuned', 'device', 'toc', 'cover', 'final_name', 'audiobook'
            ]

            for field in restore_fields:
                if field in checkpoint_data and checkpoint_data[field] is not None:
                    self.session[field] = checkpoint_data[field]

            # Restore metadata
            if 'metadata' in checkpoint_data:
                for key, value in checkpoint_data['metadata'].items():
                    if value is not None:
                        self.session['metadata'][key] = value

            stage = checkpoint_data.get('stage', 'unknown')
            timestamp = checkpoint_data.get('timestamp', 'unknown')
            print(f"✓ Checkpoint restored: {stage} (saved at {timestamp})")

            return True

        except Exception as e:
            print(f"Warning: Failed to restore from checkpoint: {e}")
            return False

    def get_checkpoint_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the current checkpoint without restoring.

        Returns:
            Optional[Dict]: Checkpoint info if available, None otherwise
        """
        checkpoint_data = self.load_checkpoint()
        if not checkpoint_data:
            return None

        return {
            'stage': checkpoint_data.get('stage'),
            'timestamp': checkpoint_data.get('timestamp'),
            'ebook': checkpoint_data.get('ebook'),
            'chapters_count': checkpoint_data.get('chapters_count'),
            'session_id': checkpoint_data.get('session_id')
        }

    def delete_checkpoint(self) -> bool:
        """
        Delete the checkpoint file.

        Returns:
            bool: True if deleted successfully or doesn't exist, False otherwise
        """
        try:
            if self.checkpoint_path and os.path.exists(self.checkpoint_path):
                os.remove(self.checkpoint_path)
                print("✓ Checkpoint deleted")
            return True
        except Exception as e:
            print(f"Warning: Failed to delete checkpoint: {e}")
            return False

    @staticmethod
    def _serialize_dict(data: Any) -> Any:
        """Recursively convert proxy dicts/lists to regular Python objects."""
        if hasattr(data, 'items'):  # Dict-like
            return {k: CheckpointManager._serialize_dict(v) for k, v in data.items()}
        elif hasattr(data, '__iter__') and not isinstance(data, (str, bytes)):  # List-like
            return [CheckpointManager._serialize_dict(item) for item in data]
        else:
            return data

    @staticmethod
    def find_existing_checkpoint(process_dir: str) -> bool:
        """
        Check if a checkpoint exists for a given process directory.

        Args:
            process_dir: The process directory path

        Returns:
            bool: True if checkpoint exists, False otherwise
        """
        checkpoint_path = os.path.join(process_dir, CheckpointManager.CHECKPOINT_FILE)
        return os.path.exists(checkpoint_path)
