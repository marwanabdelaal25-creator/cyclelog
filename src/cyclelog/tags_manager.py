"""Bulk tag operations across bikes.

Author: Marwan Helmy
"""

from __future__ import annotations

from typing import Iterable, Optional

from .errors import NotFoundError, ValidationError
from .storage import JsonStorage


class TagsManager:
    def __init__(self, storage: JsonStorage):
        self.storage = storage

    def ensure_tag(self, name: str, color: str = "") -> dict:
        name = name.strip().lower()
        if not name:
            raise ValidationError("tag name empty")
        for tag in self.storage.list_tags():
            if tag.get("name", "").lower() == name:
                return tag
        return self.storage.create_tag({"name": name, "color": color})

    def add_to_bike(self, bike_id: str, tag: str) -> dict:
        bike = self.storage.get_bike(bike_id)
        self.ensure_tag(tag)
        tags = list(bike.tag_ids)
        t = tag.strip().lower()
        if t not in tags:
            tags.append(t)
        return self.storage.update_bike(bike_id, {"tag_ids": tags}).to_dict()

    def remove_from_bike(self, bike_id: str, tag: str) -> dict:
        bike = self.storage.get_bike(bike_id)
        t = tag.strip().lower()
        tags = [x for x in bike.tag_ids if x != t]
        return self.storage.update_bike(bike_id, {"tag_ids": tags}).to_dict()

    def bulk_add(self, bike_ids: Iterable[str], tag: str) -> list[dict]:
        results = []
        for pid in bike_ids:
            try:
                results.append(self.add_to_bike(pid, tag))
            except NotFoundError:
                pass
        return results

    def bulk_remove(self, bike_ids: Iterable[str], tag: str) -> list[dict]:
        results = []
        for pid in bike_ids:
            try:
                results.append(self.remove_from_bike(pid, tag))
            except NotFoundError:
                pass
        return results

    def bikes_with_tag(self, tag: str) -> list[dict]:
        t = tag.strip().lower()
        return [
            p.to_dict()
            for p in self.storage.list_bikes(active_only=False)
            if t in [x.lower() for x in p.tag_ids]
        ]

    def rename_tag(self, old_name: str, new_name: str) -> int:
        old = old_name.strip().lower()
        new = new_name.strip().lower()
        if not new:
            raise ValidationError("new tag name empty")
        count = 0
        for bike in self.storage.list_bikes(active_only=False):
            tags = [new if x.lower() == old else x for x in bike.tag_ids]
            if tags != bike.tag_ids:
                self.storage.update_bike(bike.id, {"tag_ids": tags})
                count += 1
        for tag in self.storage.list_tags():
            if tag.get("name", "").lower() == old:
                self.storage.update_tag(tag["id"], {"name": new})
        if count == 0 and old != new:
            self.ensure_tag(new)
        return count

    def unused_tags(self) -> list[str]:
        defined = {t.get("name", "").lower() for t in self.storage.list_tags()}
        used = set()
        for bike in self.storage.list_bikes(active_only=False):
            used.update(x.lower() for x in bike.tag_ids)
        return sorted(defined - used)

    def tag_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for bike in self.storage.list_bikes(active_only=False):
            for t in bike.tag_ids:
                key = t.lower()
                counts[key] = counts.get(key, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))

    def merge_tags(self, source: str, target: str) -> int:
        src = source.strip().lower()
        tgt = target.strip().lower()
        self.ensure_tag(tgt)
        changed = 0
        for bike in self.storage.list_bikes(active_only=False):
            tags = list(bike.tag_ids)
            if src not in [x.lower() for x in tags]:
                continue
            new_tags = []
            seen = set()
            for x in tags:
                val = tgt if x.lower() == src else x
                lk = val.lower()
                if lk not in seen:
                    new_tags.append(val)
                    seen.add(lk)
            self.storage.update_bike(bike.id, {"tag_ids": new_tags})
            changed += 1
        return changed
