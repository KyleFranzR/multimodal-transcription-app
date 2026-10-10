import os
import shutil
import time
from pathlib import Path


class StorageManager:
    def __init__(self, temp_dir_name: str = "temp"):
        # Resolves to project root / storage / temp
        self.package_root = Path(__file__).resolve().parents[2]
        self.storage_dir = self.package_root / "storage"
        self.temp_dir = self.storage_dir / temp_dir_name

        self._ensure_directories()

    def _ensure_directories(self):
        """Creates storage and temp directories if they do not exist."""
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def cleanup_temp(self, max_age_seconds: int = 86400):
        """Cleans up temporary files older than max_age_seconds (default 24h)."""
        if not self.temp_dir.exists():
            return

        now = time.time()
        for item in self.temp_dir.glob("*"):
            if item.is_file():
                if now - item.stat().st_mtime > max_age_seconds:
                    try:
                        item.unlink()
                    except OSError as e:
                        print(f"Error deleting temp file {item}: {e}")

    def purge_all_temp(self):
        """Empties the temporary folder completely."""
        if self.temp_dir.exists():
            for item in self.temp_dir.glob("*"):
                try:
                    if item.is_file():
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item)
                except OSError as e:
                    print(f"Error purging {item}: {e}")

    def get_temp_file_path(self, filename: str) -> Path:
        """Returns a Path object for a named file inside storage/temp/."""
        return self.temp_dir / filename


if __name__ == "__main__":
    print("Testing StorageManager...")
    storage = StorageManager()
    print(f"✓ Temp directory resolved and ready at: {storage.temp_dir}")
    
    # Test file path generation and cleanup
    test_file = storage.get_temp_file_path("test_session.txt")
    test_file.write_text("Caecus session initialization test.")
    print(f"✓ Created test file at: {test_file}")

    storage.purge_all_temp()
    print("✓ Purged temp directory successfully!")