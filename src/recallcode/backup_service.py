import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from recallcode.database import DATABASE_URL
from recallcode.note_service import NOTES_DIR

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BACKUP_DIR = PROJECT_ROOT / "backups"
DATABASE_ARCHIVE_PATH = "data/recallcode.db"


def _database_path() -> Path:
    """Resolve the SQLite database path from DATABASE_URL."""
    prefix = "sqlite:///"

    if not DATABASE_URL.startswith(prefix):
        raise ValueError("Backup currently supports SQLite databases only.")

    path = Path(DATABASE_URL.removeprefix(prefix))

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    return path.resolve()


def create_backup(
    *,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
    database_path: Path | None = None,
    notes_dir: Path = NOTES_DIR,
) -> Path:
    """Create a timestamped ZIP backup of the database and Markdown notes."""
    source_db = Path(database_path) if database_path else _database_path()

    if not source_db.is_file():
        raise FileNotFoundError(f"Database not found: {source_db}")

    backup_dir = Path(backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_dir / f"recallcode-backup-{timestamp}.zip"

    try:
        with tempfile.TemporaryDirectory() as temporary_dir:
            snapshot_path = Path(temporary_dir) / "recallcode.db"

            # SQLite's backup API creates a consistent database snapshot.
            with (
                sqlite3.connect(source_db) as source,
                sqlite3.connect(snapshot_path) as destination,
            ):
                source.backup(destination)

            with zipfile.ZipFile(
                backup_path,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
            ) as archive:
                archive.write(
                    snapshot_path,
                    arcname=DATABASE_ARCHIVE_PATH,
                )

                if notes_dir.exists():
                    if not notes_dir.is_dir():
                        raise ValueError("Notes path must be a directory.")

                    for path in notes_dir.rglob("*"):
                        if path.is_symlink():
                            raise ValueError(
                                "Backup does not support symlinks in notes."
                            )

                        if path.is_file():
                            archive.write(
                                path,
                                arcname=(Path("notes") / path.relative_to(notes_dir)),
                            )

        return backup_path

    except Exception:
        backup_path.unlink(missing_ok=True)
        raise


def _validate_archive(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    """Reject unsafe paths, symlinks, duplicates, and unexpected files."""
    entries = archive.infolist()
    seen: set[str] = set()
    database_found = False

    for entry in entries:
        name = entry.filename

        if name in seen:
            raise ValueError(f"Duplicate archive entry: {name}")
        seen.add(name)

        path = PurePosixPath(name)

        if path.is_absolute() or ".." in path.parts or not path.parts or "\\" in name:
            raise ValueError(f"Unsafe archive path: {name}")

        if name == DATABASE_ARCHIVE_PATH:
            if entry.is_dir():
                raise ValueError("Database entry must be a file.")
            database_found = True
        elif name == "notes" and entry.is_dir():
            continue
        elif path.parts[0] == "notes" and len(path.parts) >= 2:
            pass
        else:
            raise ValueError(f"Unexpected archive entry: {name}")

        unix_mode = entry.external_attr >> 16
        if stat.S_ISLNK(unix_mode):
            raise ValueError(f"Symlinks are not supported: {name}")

    if not database_found:
        raise ValueError("Backup does not contain the database.")

    return entries


def _validate_database(path: Path) -> None:
    """Check SQLite integrity and foreign-key consistency."""
    with sqlite3.connect(path) as connection:
        result = connection.execute("PRAGMA integrity_check").fetchone()

        if result is None or result[0] != "ok":
            raise ValueError("Backup database failed its integrity check.")

        violations = connection.execute("PRAGMA foreign_key_check").fetchall()

        if violations:
            raise ValueError("Backup database contains foreign-key violations.")

        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }

        required_tables = {
            "alembic_version",
            "attempts",
            "problem_topics",
            "problems",
            "reviews",
            "topics",
        }

        if not required_tables.issubset(tables):
            raise ValueError("Backup database is missing required tables.")


def restore_backup(
    backup_path: Path,
    *,
    database_path: Path | None = None,
    notes_dir: Path = NOTES_DIR,
    backup_dir: Path = DEFAULT_BACKUP_DIR,
    confirm: bool = False,
) -> Path:
    """
    Restore a backup after validation and creation of a safety backup.

    Stop the Streamlit app before restoring. The caller must explicitly
    pass confirm=True because this operation replaces existing data.
    """
    if not confirm:
        raise ValueError(
            "Restoration replaces existing data. Pass confirm=True to proceed."
        )

    backup_path = Path(backup_path).resolve()
    target_db = Path(database_path).resolve() if database_path else _database_path()
    notes_dir = Path(notes_dir).resolve()

    if not backup_path.is_file():
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    if not target_db.is_file():
        raise FileNotFoundError(f"Target database not found: {target_db}")

    if backup_path == target_db:
        raise ValueError("Backup archive cannot be the target database.")

    target_db.parent.mkdir(parents=True, exist_ok=True)
    notes_dir.parent.mkdir(parents=True, exist_ok=True)

    # Validate and stage everything before changing live data.
    with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temporary_dir:
        staging = Path(temporary_dir)
        staged_db = staging / "restored.db"
        staged_notes = staging / "notes"
        staged_notes.mkdir()

        with zipfile.ZipFile(backup_path, "r") as archive:
            entries = _validate_archive(archive)

            for entry in entries:
                if entry.is_dir():
                    continue

                destination = (
                    staged_db
                    if entry.filename == DATABASE_ARCHIVE_PATH
                    else staged_notes.joinpath(*PurePosixPath(entry.filename).parts[1:])
                )

                destination.parent.mkdir(parents=True, exist_ok=True)

                with (
                    archive.open(entry) as source,
                    destination.open("wb") as target,
                ):
                    shutil.copyfileobj(source, target)

        _validate_database(staged_db)

        # Preserve current state in a separate backup before restoration.
        safety_backup = create_backup(
            backup_dir=backup_dir,
            database_path=target_db,
            notes_dir=notes_dir,
        )

        old_db = staging / "previous.db"
        old_notes = staging / "previous_notes"
        moved_old_db = False
        moved_old_notes = False
        installed_db = False
        installed_notes = False

        try:
            # The application must be stopped to avoid stale DB connections.
            os.replace(target_db, old_db)
            moved_old_db = True

            if notes_dir.exists():
                os.replace(notes_dir, old_notes)
                moved_old_notes = True

            os.replace(staged_db, target_db)
            installed_db = True

            os.replace(staged_notes, notes_dir)
            installed_notes = True

            # SQLite sidecars from the old database must not survive restore.
            Path(f"{target_db}-wal").unlink(missing_ok=True)
            Path(f"{target_db}-shm").unlink(missing_ok=True)

        except Exception:
            # Best-effort rollback if installing the restored files fails.
            if installed_notes and notes_dir.exists():
                shutil.rmtree(notes_dir)

            if installed_db and target_db.exists():
                target_db.unlink()

            if moved_old_db and old_db.exists():
                os.replace(old_db, target_db)

            if moved_old_notes and old_notes.exists():
                os.replace(old_notes, notes_dir)

            raise

    return safety_backup
