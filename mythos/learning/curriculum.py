"""
Curriculum scheduler — orders training targets from easy → hard.

Difficulty is a weighted blend of:
  * lines of code,
  * dependency surface,
  * historical success rate of similar repos.

Used by the data-flywheel to feed RL / LoRA fine-tuning with progressively
harder workloads.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


@dataclass
class CurriculumItem:
    repo: str
    loc: int
    dep_count: int
    historical_success: float = 0.0  # 0..1

    @property
    def difficulty(self) -> float:
        return (
            0.5 * math.log1p(self.loc)
            + 0.3 * math.log1p(self.dep_count)
            + 0.2 * (1.0 - self.historical_success)
        )


class CurriculumScheduler:
    def __init__(self, items: list[CurriculumItem] | None = None):
        self.items: list[CurriculumItem] = items or []

    def add(self, repo: str, loc: int, dep_count: int, success: float = 0.0) -> None:
        self.items.append(CurriculumItem(repo, loc, dep_count, success))

    def next_batch(self, batch_size: int = 4) -> list[CurriculumItem]:
        self.items.sort(key=lambda i: i.difficulty)
        return self.items[:batch_size]

    def to_dict(self) -> dict[str, Any]:
        return {"items": [i.__dict__ | {"difficulty": i.difficulty} for i in self.items]}
