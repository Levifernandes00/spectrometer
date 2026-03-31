import argparse

from dotenv import load_dotenv

load_dotenv()

from config import load_config
from device import find_or_create_device, get_local_db, get_supabase
from ingest import process_folder
from watcher import watch_folder


def main(config: dict, once: bool = False) -> None:
    supabase = get_supabase(config)
    if supabase:
        print("Connected to Supabase")

    local_db = get_local_db(config)
    if local_db:
        print("Connected to local database:", config["database"])
        local_db.close()

    device = find_or_create_device(config)
    if device:
        print("Device:", device.get("name"), "| identifier:", device.get("identifier"))

    if once:
        processed = process_folder(config)
        print(f"Processed {processed} file(s)")
        if processed > 0:
            print("Results inserted into database.")
    else:
        watch_folder(config)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one scan and exit (default: run continuous watcher).",
    )
    args = parser.parse_args()

    config = load_config()
    main(config, once=args.once)
