import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class Meme:
    filename: str
    name: str
    tags: list[str]
    created_at: str


class MemeConfig:
    def __init__(self, memes_dir: str):
        self.memes_dir = Path(memes_dir)
        self.config_file = self.memes_dir / "memes.json"
        self.emotions_file = self.memes_dir / "config.json"
        self._memes: dict[str, Meme] = {}
        self._emotions: list[str] = []
        self._load()
        self._load_emotions()

    def _load(self) -> None:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for filename, meme_data in data.items():
                        self._memes[filename] = Meme(
                            filename=filename,
                            name=meme_data.get("name", ""),
                            tags=meme_data.get("tags", []),
                            created_at=meme_data.get("created_at", "")
                        )
            except (json.JSONDecodeError, KeyError):
                self._memes = {}
        else:
            self._memes = {}

    def _save(self) -> None:
        data = {
            filename: {
                "name": meme.name,
                "tags": meme.tags,
                "created_at": meme.created_at
            }
            for filename, meme in self._memes.items()
        }
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_meme(self, filename: str, name: str, tags: list[str], created_at: str) -> Meme:
        meme = Meme(filename=filename, name=name, tags=tags, created_at=created_at)
        self._memes[filename] = meme
        self._save()
        return meme

    def update_meme(self, filename: str, name: Optional[str] = None, tags: Optional[list[str]] = None) -> Optional[Meme]:
        if filename not in self._memes:
            return None
        
        meme = self._memes[filename]
        if name is not None:
            meme.name = name
        if tags is not None:
            meme.tags = tags
        self._save()
        return meme

    def delete_meme(self, filename: str) -> bool:
        if filename not in self._memes:
            return False
        
        file_path = self.memes_dir / filename
        if file_path.exists():
            file_path.unlink()
        del self._memes[filename]
        self._save()
        return True

    def get_meme(self, filename: str) -> Optional[Meme]:
        return self._memes.get(filename)

    def get_all_memes(self) -> list[Meme]:
        return list(self._memes.values())

    def search_by_tag(self, tag: str) -> list[Meme]:
        tag = tag.lower()
        return [meme for meme in self._memes.values() if tag in [t.lower() for t in meme.tags]]

    def search(self, keyword: str) -> list[Meme]:
        keyword = keyword.lower()
        results = []
        for meme in self._memes.values():
            if keyword in meme.name.lower():
                results.append(meme)
            elif any(keyword in tag.lower() for tag in meme.tags):
                results.append(meme)
        return results

    def get_all_tags(self) -> set[str]:
        tags = set()
        for meme in self._memes.values():
            tags.update(meme.tags)
        return tags

    def _load_emotions(self) -> None:
        if self.emotions_file.exists():
            try:
                with open(self.emotions_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._emotions = data.get("emotions", [])
            except (json.JSONDecodeError, KeyError):
                self._emotions = []
        else:
            self._emotions = []

    def get_emotions(self) -> list[str]:
        return list(self._emotions)
