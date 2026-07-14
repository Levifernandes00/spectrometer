"""Background folder watcher for spectrometer ingestion."""

from pathlib import Path
import time

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from ingest import process_folder


def is_supported_file(path: str | Path) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in {".pdf", ".txt"}


def handle_folder_change(config: dict, changed_path: Path) -> None:
    """Process folder changes triggered by watcher events."""
    try:
        processed = process_folder(config, changed_path=changed_path)
        if processed > 0:
            print(f"Processed {processed} file(s)")
    except OSError as exc:
        print(f"Error processing {changed_path}: {exc}")
    except Exception as exc:
        print(f"Unexpected error processing {changed_path}: {exc}")


class SpectrometerEventHandler(FileSystemEventHandler):
    """Handles created/moved files and triggers ingestion callback."""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def _handle_path(self, path: str) -> None:
        if is_supported_file(path):
            self.callback(Path(path))

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle_path(event.src_path)

    def on_moved(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._handle_path(event.dest_path)


def watch_folder(config: dict) -> None:
    """Run long-lived watcher and process files when new assets arrive."""
    folder_path = config.get("folder")
    if not folder_path:
        print("No folder configured, watcher not started.")
        return

    folder = Path(folder_path)
    if not folder.is_dir():
        print(f"Configured folder does not exist: {folder}")
        return

    def on_change(changed_path: Path) -> None:
        handle_folder_change(config, changed_path)

    # Initial sync for any pre-existing files.
    try:
        processed = process_folder(config)
        if processed > 0:
            print(f"Processed {processed} file(s)")
    except OSError as exc:
        print(f"Error during initial folder scan: {exc}")
    except Exception as exc:
        print(f"Unexpected error during initial folder scan: {exc}")

    observer = Observer()
    observer.schedule(SpectrometerEventHandler(on_change), str(folder), recursive=True)
    observer.start()
    print(f"Watching folder: {folder}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping watcher...")
    finally:
        observer.stop()
        observer.join()
