"""Scan folder, parse files, and insert results into the database."""

from pathlib import Path

from config import load_config
from device import find_or_create_device, get_local_db, get_supabase
from db import (
    _date_to_iso,
    find_or_create_batch_local,
    find_or_create_batch_supabase,
    has_results_for_device_datetime_local,
    has_results_for_device_datetime_supabase,
    insert_results_local,
    insert_results_supabase,
    _ensure_tables_local,
)
from parser import find_files, parse_file


def process_folder(config: dict) -> int:
    """
    Read all files in config folder, parse each, and insert results into DB.
    Uses Supabase if configured, otherwise local DB.
    Returns the number of files processed.
    """
    folder_path = config.get("folder")
    if not folder_path:
        return 0

    folder = Path(folder_path)
    if not folder.is_dir():
        return 0

    device = find_or_create_device(config)
    if not device:
        return 0

    device_id = device.get("id")
    if not device_id:
        return 0

    supabase = get_supabase(config)
    local_db = get_local_db(config)

    if local_db:
        _ensure_tables_local(local_db)

    processed = 0
    files = find_files(folder)

    for path in files:
        parsed = parse_file(path)
        if not parsed:
            continue

        datetime_iso = _date_to_iso(parsed.date, parsed.time)
        results = [
            {"key": k, "value": v, "obs": None}
            for k, v in parsed.results.items()
        ]

        if not results:
            continue

        if supabase:
            if has_results_for_device_datetime_supabase(supabase, device_id, datetime_iso):
                continue
            batch = find_or_create_batch_supabase(
                supabase,
                parsed.batch,
                parsed.date,
            )
            insert_results_supabase(
                supabase,
                batch["id"],
                device_id,
                results,
                datetime_iso,
            )
            processed += 1
        elif local_db:
            if has_results_for_device_datetime_local(local_db, device_id, datetime_iso):
                continue
            batch = find_or_create_batch_local(
                local_db,
                parsed.batch,
                parsed.date,
            )
            insert_results_local(
                local_db,
                batch["id"],
                device_id,
                results,
                datetime_iso,
            )
            processed += 1

    if local_db:
        local_db.close()

    return processed
