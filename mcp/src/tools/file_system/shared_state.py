"""Shared state management for file system tools."""

import os
from typing import Dict
from threading import Lock


class FileTimestampTracker:
    """Tracks file read timestamps across different tools."""
    
    def __init__(self):
        self._read_timestamps: Dict[str, float] = {}
        self._lock = Lock()
    
    def mark_file_read(self, file_path: str) -> None:
        """Mark a file as having been read at the current timestamp."""
        if not os.path.exists(file_path):
            return
        
        # Convert to absolute path for consistency
        abs_path = os.path.abspath(file_path)
        current_mtime = os.path.getmtime(abs_path)
        
        with self._lock:
            self._read_timestamps[abs_path] = current_mtime
    
    def get_read_timestamp(self, file_path: str) -> float | None:
        """Get the timestamp when a file was last read."""
        abs_path = os.path.abspath(file_path)
        with self._lock:
            return self._read_timestamps.get(abs_path)
    
    def was_file_read(self, file_path: str) -> bool:
        """Check if a file has been read."""
        abs_path = os.path.abspath(file_path)
        with self._lock:
            return abs_path in self._read_timestamps
    
    def is_file_modified_since_read(self, file_path: str) -> bool:
        """Check if a file has been modified since it was last read."""
        if not os.path.exists(file_path):
            return False
        
        abs_path = os.path.abspath(file_path)
        read_timestamp = self.get_read_timestamp(abs_path)
        
        if read_timestamp is None:
            return True  # File was never read, so consider it "modified"
        
        current_mtime = os.path.getmtime(abs_path)
        return current_mtime > read_timestamp
    
    def clear_timestamp(self, file_path: str) -> None:
        """Clear the read timestamp for a file."""
        abs_path = os.path.abspath(file_path)
        with self._lock:
            self._read_timestamps.pop(abs_path, None)
    
    def clear_all(self) -> None:
        """Clear all read timestamps."""
        with self._lock:
            self._read_timestamps.clear()


# Global instance to be shared across tools
_global_tracker: FileTimestampTracker | None = None


def get_file_tracker() -> FileTimestampTracker:
    """Get the global file timestamp tracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = FileTimestampTracker()
    return _global_tracker 