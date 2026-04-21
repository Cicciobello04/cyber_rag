from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class ReportStore:
    def __init__(self, history_file: str):
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self.history_file.write_text("[]", encoding="utf-8")

    def _read(self) -> List[Dict[str, Any]]:
        return json.loads(self.history_file.read_text(encoding="utf-8"))

    def _write(self, items: List[Dict[str, Any]]) -> None:
        self.history_file.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    def add(self, report: Dict[str, Any]) -> None:
        items = self._read()
        items.insert(0, report)
        self._write(items)

    def list_all(self) -> List[Dict[str, Any]]:
        return self._read()

    def get(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        for item in self._read():
            if item.get("analysis_id") == analysis_id:
                return item
        return None
