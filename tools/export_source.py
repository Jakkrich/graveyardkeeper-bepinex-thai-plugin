"""Export the supported English locale from a locally owned GK1 installation."""
import argparse
import csv
from pathlib import Path

import UnityPy

from build_payload import RESOURCE_HASH, decode_locale, sha


def export(game_root, output):
    asset = game_root / "Graveyard Keeper_Data/resources.assets"
    if sha(asset) != RESOURCE_HASH:
        raise ValueError("Unsupported or modified resources.assets")
    objects = {obj.path_id: obj for obj in UnityPy.load(str(asset)).objects}
    locale = decode_locale(objects[150186].get_raw_data())
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("key", "value"))
        writer.writeheader()
        writer.writerows(
            {"key": key, "value": value}
            for key, value in zip(locale["keys"], locale["texts"])
        )
    print(f"Exported {len(locale['keys'])} rows: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / ".local/source_en.csv",
    )
    args = parser.parse_args()
    export(args.game_root.resolve(), args.output.resolve())
