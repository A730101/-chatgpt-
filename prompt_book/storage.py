"""Persistent storage for prompt notebooks."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional


ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class PromptNotFoundError(LookupError):
    """Raised when a prompt cannot be located in the notebook."""


@dataclass
class Prompt:
    """Dataclass representing a stored prompt."""

    id: str
    title: str
    category: str
    content: str
    notes: str = ""
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def create(
        cls, title: str, category: str, content: str, notes: str = ""
    ) -> "Prompt":
        now = _now()
        return cls(
            id=str(uuid.uuid4()),
            title=title,
            category=category,
            content=content,
            notes=notes,
            created_at=now,
            updated_at=now,
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "content": self.content,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "Prompt":
        return cls(
            id=data["id"],
            title=data["title"],
            category=data.get("category", "uncategorized"),
            content=data.get("content", ""),
            notes=data.get("notes", ""),
            created_at=data.get("created_at", _now()),
            updated_at=data.get("updated_at", _now()),
        )


class PromptBook:
    """Manage prompts stored on disk in a structured JSON document."""

    def __init__(self, path: Path | str = "prompts.json") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: Dict[str, object] = {"metadata": {"categories": []}, "prompts": []}
        if self.path.exists():
            self._load()
        else:
            self._save()

    # ------------------------------------------------------------------
    # basic helpers
    def _load(self) -> None:
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Prompt notebook at {self.path} is not valid JSON"
            ) from exc

        metadata = raw.get("metadata") if isinstance(raw, dict) else None
        prompts = raw.get("prompts") if isinstance(raw, dict) else None
        if not isinstance(metadata, dict) or not isinstance(prompts, list):
            raise ValueError("Prompt notebook has an unexpected structure")

        categories = metadata.get("categories", [])
        if not isinstance(categories, list):
            categories = []

        self._data = {
            "metadata": {"categories": categories},
            "prompts": [Prompt.from_dict(item) for item in prompts if isinstance(item, dict)],
        }

    def _save(self) -> None:
        serializable = {
            "metadata": self.metadata,
            "prompts": [prompt.to_dict() for prompt in self.prompts],
        }
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(serializable, fh, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # properties
    @property
    def metadata(self) -> Dict[str, object]:
        return self._data.setdefault("metadata", {"categories": []})  # type: ignore[return-value]

    @property
    def prompts(self) -> List[Prompt]:
        return self._data.setdefault("prompts", [])  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # category helpers
    def list_categories(self) -> List[str]:
        explicit = [str(item) for item in self.metadata.get("categories", [])]
        derived = {prompt.category for prompt in self.prompts}
        return sorted({*explicit, *derived})

    def add_category(self, name: str) -> None:
        categories = self.metadata.setdefault("categories", [])  # type: ignore[assignment]
        if name not in categories:
            categories.append(name)
            self._save()

    def remove_category(self, name: str) -> None:
        categories = self.metadata.setdefault("categories", [])  # type: ignore[assignment]
        if name in categories:
            categories.remove(name)
            self._save()

    # ------------------------------------------------------------------
    # prompt operations
    def add_prompt(self, title: str, category: str, content: str, notes: str = "") -> Prompt:
        prompt = Prompt.create(title=title, category=category, content=content, notes=notes)
        self.prompts.append(prompt)
        self.add_category(category)
        self._save()
        return prompt

    def get_prompt(self, prompt_id: str) -> Prompt:
        for prompt in self.prompts:
            if prompt.id == prompt_id:
                return prompt
        raise PromptNotFoundError(f"Prompt with id {prompt_id} was not found")

    def list_prompts(
        self,
        category: Optional[str] = None,
        *,
        search: Optional[str] = None,
        sort_by: str = "updated",
        descending: bool = True,
    ) -> List[Prompt]:
        prompts = list(self.prompts)

        if category is not None:
            prompts = [prompt for prompt in prompts if prompt.category == category]

        if search:
            needle = search.casefold()
            prompts = [
                prompt
                for prompt in prompts
                if _matches(prompt, needle)
            ]

        prompts.sort(key=_sort_key(sort_by), reverse=descending)
        return prompts

    def update_prompt(
        self,
        prompt_id: str,
        *,
        title: Optional[str] = None,
        category: Optional[str] = None,
        content: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Prompt:
        prompt = self.get_prompt(prompt_id)
        if title is not None:
            prompt.title = title
        if category is not None:
            prompt.category = category
            self.add_category(category)
        if content is not None:
            prompt.content = content
        if notes is not None:
            prompt.notes = notes
        prompt.updated_at = _now()
        self._save()
        return prompt

    def delete_prompt(self, prompt_id: str) -> None:
        before = len(self.prompts)
        self._data["prompts"] = [prompt for prompt in self.prompts if prompt.id != prompt_id]
        if len(self.prompts) == before:
            raise PromptNotFoundError(f"Prompt with id {prompt_id} was not found")
        self._save()


# ----------------------------------------------------------------------
# helper utilities

def _now() -> str:
    return datetime.now(timezone.utc).strftime(ISO_FORMAT)


def _matches(prompt: Prompt, needle: str) -> bool:
    haystacks = (
        prompt.title,
        prompt.category,
        prompt.content,
        prompt.notes,
    )
    return any(needle in (value or "").casefold() for value in haystacks)


def _sort_key(field: str) -> Callable[[Prompt], object]:
    key_map: Dict[str, Callable[[Prompt], object]] = {
        "updated": lambda prompt: _parse_datetime(prompt.updated_at),
        "created": lambda prompt: _parse_datetime(prompt.created_at),
        "title": lambda prompt: prompt.title.casefold(),
        "category": lambda prompt: prompt.category.casefold(),
    }
    if field not in key_map:
        raise ValueError(
            "sort_by must be one of 'updated', 'created', 'title', or 'category'"
        )
    return key_map[field]


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.strptime(value, ISO_FORMAT)
    except ValueError:
        return datetime.min
