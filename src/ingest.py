"""Scan folder, parse files, and insert results into the database."""

import json
from pathlib import Path

from device import (
    find_or_create_device,
    get_company_id,
    get_local_company_id,
    get_local_db,
    get_supabase,
)
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
from parser import ParsedFile, find_files, parse_file
from websocket_publisher import publish_batch_material


def _build_result_obs(parsed: ParsedFile) -> str:
    """Oxpecker-compatible metadata JSON for result.obs."""
    return json.dumps(
        {
            "fusion": parsed.batch,
            "material": parsed.material,
            "furnace": parsed.furnace or "",
            "date": parsed.date,
            "hour": parsed.time,
        }
    )


def process_folder(config: dict, changed_path: Path | None = None) -> int:
    """
    Read all files in config folder, parse each, and insert results into DB.
    Uses Supabase if configured, otherwise local DB.
    When changed_path is provided, that file is processed first.
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
    company_id = get_company_id(config, supabase) if supabase else None
    if supabase and not company_id:
        supabase = None

    local_db = get_local_db(config)
    local_company_id = get_local_company_id(config)

    if local_db:
        _ensure_tables_local(local_db)

    processed = 0
    files = find_files(folder)
    if changed_path is not None:
        changed = Path(changed_path)
        files = [changed] + [path for path in files if path != changed]

    for path in files:
        parsed = parse_file(path)
        if not parsed:
            continue

        datetime_iso = _date_to_iso(parsed.date, parsed.time)
        result_obs = _build_result_obs(parsed)
        results = [
            {"key": k, "value": v, "obs": result_obs}
            for k, v in parsed.results.items()
        ]

        if not results:
            continue

        if supabase and company_id:
            if has_results_for_device_datetime_supabase(supabase, device_id, datetime_iso):
                continue
            batch = find_or_create_batch_supabase(
                supabase,
                parsed.batch,
                parsed.date,
                company_id,
            )
            insert_results_supabase(
                supabase,
                batch["id"],
                device_id,
                results,
                datetime_iso,
            )
            publish_batch_material(config, parsed.batch, parsed.material)
            processed += 1
        elif local_db:
            if has_results_for_device_datetime_local(local_db, device_id, datetime_iso):
                continue
            batch = find_or_create_batch_local(
                local_db,
                parsed.batch,
                parsed.date,
                local_company_id,
            )
            insert_results_local(
                local_db,
                batch["id"],
                device_id,
                results,
                datetime_iso,
            )
            publish_batch_material(config, parsed.batch, parsed.material)
            processed += 1

    if local_db:
        local_db.close()

    return processed
