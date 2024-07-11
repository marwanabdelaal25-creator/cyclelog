"""Bike groupings / collections (e.g. kitchen herbs).

Author: Marwan Helmy
"""

from __future__ import annotations

import uuid
from typing import Iterable, Optional

from .errors import NotFoundError, ValidationError
from .storage import JsonStorage


class CollectionManager:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def create(self, name: str, description: str = "", bike_ids: Optional[Iterable[str]] = None) -> dict:
        if not name.strip():
            raise ValidationError("collection name required")
        ids = list(bike_ids or [])
        for pid in ids:
            self.storage.get_bike(pid)
        return self.storage.create_collection({
            "id": uuid.uuid4().hex[:12],
            "name": name.strip(),
            "description": description,
            "bike_ids": ids,
        })

    def list_all(self) -> list[dict]:
        return self.storage.list_collections()

    def get(self, collection_id: str) -> dict:
        for c in self.list_all():
            if c.get("id") == collection_id:
                return c
        raise NotFoundError("collections", collection_id)

    def add_bike(self, collection_id: str, bike_id: str) -> dict:
        coll = self.get(collection_id)
        self.storage.get_bike(bike_id)
        ids = list(coll.get("bike_ids", []))
        if bike_id not in ids:
            ids.append(bike_id)
        return self.storage.update_collection(collection_id, {"bike_ids": ids})

    def remove_bike(self, collection_id: str, bike_id: str) -> dict:
        coll = self.get(collection_id)
        ids = [x for x in coll.get("bike_ids", []) if x != bike_id]
        return self.storage.update_collection(collection_id, {"bike_ids": ids})

    def rename(self, collection_id: str, name: str) -> dict:
        if not name.strip():
            raise ValidationError("name required")
        return self.storage.update_collection(collection_id, {"name": name.strip()})

    def delete(self, collection_id: str) -> None:
        self.storage.delete_collection(collection_id)

    def bikes_in(self, collection_id: str) -> list[dict]:
        coll = self.get(collection_id)
        out = []
        for pid in coll.get("bike_ids", []):
            try:
                out.append(self.storage.get_bike(pid).to_dict())
            except NotFoundError:
                pass  # stale id
        return out

    def collections_for_bike(self, bike_id: str) -> list[dict]:
        return [
            c for c in self.list_all()
            if bike_id in c.get("bike_ids", [])
        ]

    def merge(self, target_id: str, source_id: str) -> dict:
        target = self.get(target_id)
        source = self.get(source_id)
        merged_ids = list(dict.fromkeys(
            list(target.get("bike_ids", [])) + list(source.get("bike_ids", []))
        ))
        self.storage.update_collection(target_id, {"bike_ids": merged_ids})
        self.delete(source_id)
        return self.get(target_id)
