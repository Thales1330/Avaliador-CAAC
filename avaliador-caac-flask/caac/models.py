"""Modelos de dados do Avaliador CAAC (atividade e processo).

As regras de cada resolução (itens, horas, limites) ficam em ``caac/resolutions.py`` e
``data/resolutions/*.json``; aqui só existem os dados que o usuário preenche.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any

APP_VERSION = "0.5.0-flask"


@dataclass
class Activity:
    """Uma atividade (certificado) de um processo."""

    id: int = 0
    item_code: int = 0
    event_name: str = ""
    event_desc: str = ""
    shift_number: float = 1.0
    ifg_event: bool = True
    institution: str = ""
    ch_presented: float = 0.0
    date: str = "-"
    ch_validated: float = 0.0
    invalidate_ch: bool = False
    show_in_report: bool = True
    ignore_restrictions: bool = False
    obs: str = ""
    # Calculado pela validação: True quando a CH foi limitada/reduzida/zerada.
    limited_ch: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Activity":
        known = {f.name: f for f in fields(cls)}
        clean: dict[str, Any] = {}
        for key, value in data.items():
            if key not in known:
                continue
            kind = known[key].type
            if kind in ("bool", bool):
                clean[key] = bool(value)
            elif kind in ("int", int):
                clean[key] = _to_int(value)
            elif kind in ("float", float):
                clean[key] = _to_float(value)
            else:
                clean[key] = "" if value is None else str(value)
        return cls(**clean)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Process:
    """Um processo de avaliação de atividades complementares."""

    protocol: str = ""
    student_name: str = ""
    resolution: int = 0  # id da resolução (<NumResolucao> no XML); veja caac/resolutions.py
    activities: list[Activity] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Process":
        resolution = _to_int(data.get("resolution", 0))
        return cls(
            protocol=str(data.get("protocol", "") or "").strip(),
            student_name=str(data.get("student_name", "") or "").strip(),
            resolution=resolution,
            activities=[Activity.from_dict(a) for a in data.get("activities", [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "student_name": self.student_name,
            "resolution": self.resolution,
            "activities": [a.to_dict() for a in self.activities],
        }


def _to_float(value: Any) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _to_int(value: Any) -> int:
    try:
        return int(float(str(value).replace(",", ".")))
    except (TypeError, ValueError):
        return 0
