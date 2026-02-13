from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from app.application.repositories.takeoff_repository import StoredTakeoff, TakeoffRepository
from app.domain.takeoff import Takeoff
from app.infrastructure.takeoff_json_codec import TakeoffJsonCodec


@dataclass(frozen=True)
class FileTakeoffRepository(TakeoffRepository):
    base_dir: Path
    codec: TakeoffJsonCodec = TakeoffJsonCodec()

    def __post_init__(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, takeoff: Takeoff) -> StoredTakeoff:
        takeoff_id = uuid4().hex[:12]
        path = self.base_dir / f"{takeoff_id}.json"

        payload = self.codec.to_dict(takeoff)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        return StoredTakeoff(id=takeoff_id, path=path)

    def load(self, takeoff_id: str) -> Takeoff:
        path = self.base_dir / f"{takeoff_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Takeoff not found: {takeoff_id} ({path})")

        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid takeoff JSON: top-level must be an object")

        return self.codec.from_dict(data)
