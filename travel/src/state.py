import json
import os
from datetime import datetime, timezone
from pathlib import Path


class MapState:
    def __init__(self, maps_dir: str | None = None):
        if maps_dir is None:
            maps_dir = os.path.join(os.path.dirname(__file__), "..", "maps")
        self._dir = Path(maps_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, map_id: str) -> Path:
        return self._dir / f"{map_id}.json"

    def _load(self, map_id: str) -> dict:
        p = self._path(map_id)
        if not p.exists():
            raise KeyError(f"Map '{map_id}' not found")
        return json.loads(p.read_text())

    def _save(self, data: dict) -> None:
        self._path(data["id"]).write_text(json.dumps(data, indent=2))

    def create_map(self, map_id: str, name: str) -> dict:
        if self._path(map_id).exists():
            raise ValueError(f"Map '{map_id}' already exists")
        data = {
            "id": map_id,
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "drive_file_id": None,
            "map_url": None,
            "layers": {"Eat": [], "Drink": [], "Do": []},
            "places": [],
        }
        self._save(data)
        return data

    def get_map(self, map_id: str) -> dict:
        return self._load(map_id)

    def list_maps(self) -> list[dict]:
        maps = []
        for p in sorted(self._dir.glob("*.json")):
            try:
                maps.append(json.loads(p.read_text()))
            except (json.JSONDecodeError, OSError):
                continue
        return maps

    def add_place(self, map_id: str, place: dict) -> dict:
        data = self._load(map_id)
        entry = {**place, "added_at": datetime.now(timezone.utc).isoformat()}
        data["places"].append(entry)
        self._save(data)
        return data

    def remove_place(self, map_id: str, place_name: str) -> dict:
        data = self._load(map_id)
        before = len(data["places"])
        data["places"] = [p for p in data["places"] if p["name"] != place_name]
        if len(data["places"]) == before:
            raise ValueError(f"Place '{place_name}' not found in map '{map_id}'")
        self._save(data)
        return data

    def set_drive_file_id(self, map_id: str, file_id: str) -> dict:
        data = self._load(map_id)
        data["drive_file_id"] = file_id
        data["map_url"] = (
            f"https://www.google.com/maps?q="
            f"https://drive.google.com/uc?export=download%26id={file_id}"
        )
        self._save(data)
        return data
