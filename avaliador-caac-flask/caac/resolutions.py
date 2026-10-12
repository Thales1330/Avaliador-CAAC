"""Resoluções de atividades complementares, descritas como DADOS.

Cada resolução é um arquivo ``data/resolutions/*.json``. Para acrescentar uma nova basta criar
mais um arquivo (veja a seção "Adicionando uma nova resolução" do README); nenhum código muda.

Conceitos
---------
* ``id``      número gravado no XML em ``<NumResolucao>``. Nunca reutilize nem altere o id de uma
              resolução já usada, senão processos antigos passam a ser calculados pelas regras erradas.
* ``code``    código do item **dentro da resolução** (gravado em ``<Item>``). O mesmo código pode
              significar coisas diferentes em resoluções diferentes.
* ``family``  resoluções da mesma família usam códigos com o mesmo significado (é o caso das 16 e 20).
              Só entre elas os itens são mantidos ao importar um processo anterior ou trocar a
              resolução; entre famílias diferentes os itens voltam para "Escolha o item...".

Tipos de regra (``rule.type``)
------------------------------
``fixed``        CH validada fixa (``hours``). Por padrão a CH apresentada também vira ``hours``;
                 com ``keep_presented`` ela é mantida.
``per_shift``    ``hours`` por turno/participação/apresentação (número informado pelo avaliador).
``presented``    a CH validada parte da CH apresentada.
``not_scored``   atividade não pontuada: 0 h validadas.

``restriction`` (opcional em ``per_shift`` e ``presented``) são as regras que o campo
"Ignorar restrições" desliga:
``factor``       multiplicador (0,8 = só 80 % da CH conta).
``cap_percent``  teto cumulativo, em % de ``total_ch``, para todas as atividades do mesmo ``group``
                 (na ordem da tabela). O que passar do teto é cortado.
``group``        nome do "saldo" compartilhado; se omitido, cada item tem o seu próprio.
``drop_below``   sobras menores que isso (em horas) são descartadas.
``scope``        ``all`` (padrão) ou ``non_ifg`` (só vale para eventos que não são do IFG).
                 Em ``all`` mesmo as atividades com "Ignorar restrições" consomem o saldo;
                 em ``non_ifg`` só consomem as que de fato sofrem a restrição.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

BASE_DIR = Path(__file__).resolve().parent.parent
RESOLUTIONS_DIR = BASE_DIR / "data" / "resolutions"

RULE_TYPES = ("fixed", "per_shift", "presented", "not_scored")
SCOPES = ("all", "non_ifg")


class ResolutionError(ValueError):
    """Arquivo de resolução inválido (a mensagem diz qual arquivo e qual item)."""


class UnknownResolution(ValueError):
    """Id de resolução que não existe neste programa."""


@dataclass(frozen=True)
class Restriction:
    scope: str = "all"
    factor: float = 1.0
    cap_percent: float | None = None
    group: str = ""
    drop_below: float = 0.0


@dataclass(frozen=True)
class Rule:
    type: str
    hours: float = 0.0
    keep_presented: bool = False
    restriction: Restriction | None = None


@dataclass(frozen=True)
class Item:
    code: int
    label: str
    rule: Rule
    shift_label: str | None = None   # rótulo do campo "número de turnos/participações" (None = sem campo)
    uses_ifg: bool = False
    uses_ch: bool = False

    def inputs(self) -> dict[str, Any]:
        """Campos que a interface deve habilitar para este item."""
        data: dict[str, Any] = {}
        if self.shift_label:
            data["shift"] = self.shift_label
        if self.uses_ifg:
            data["ifg"] = True
        if self.uses_ch:
            data["ch"] = True
        return data


@dataclass(frozen=True)
class ResolutionSpec:
    id: int
    number: str
    date: str
    total_ch: float
    family: str
    default: bool
    items: tuple[Item, ...]

    def item(self, code: int) -> Item | None:
        for item in self.items:
            if item.code == code:
                return item
        return None

    @property
    def codes(self) -> set[int]:
        return {item.code for item in self.items}

    @property
    def label(self) -> str:
        return f"Resolução nº {self.number}"

    @property
    def legal_ref(self) -> str:
        """Texto usado no PDF: ``16 de 26/12/2011``."""
        return f"{self.number} de {self.date}" if self.date else self.number


class ResolutionRegistry:
    """Conjunto de resoluções conhecidas, indexado pelo id."""

    def __init__(self, specs: list[ResolutionSpec]) -> None:
        if not specs:
            raise ResolutionError("Nenhuma resolução encontrada.")
        by_id: dict[int, ResolutionSpec] = {}
        for spec in specs:
            if spec.id in by_id:
                raise ResolutionError(f"Id de resolução repetido: {spec.id}.")
            by_id[spec.id] = spec
        self._by_id = dict(sorted(by_id.items()))
        # Padrão para novos processos: a marcada com "default": true (se várias, a de maior id, para que
        # uma resolução nova assuma o posto sem precisar editar a antiga); sem nenhuma marcada, a de menor id.
        defaults = [s for s in self._by_id.values() if s.default]
        self.default = defaults[-1] if defaults else next(iter(self._by_id.values()))

    def get(self, resolution_id: int) -> ResolutionSpec:
        try:
            return self._by_id[int(resolution_id)]
        except (KeyError, TypeError, ValueError):
            raise UnknownResolution(
                f"Resolução desconhecida (id {resolution_id}). O arquivo pode ter sido criado por uma "
                "versão mais nova do programa ou falta o arquivo dessa resolução em data/resolutions/."
            ) from None

    def __iter__(self) -> Iterator[ResolutionSpec]:
        return iter(self._by_id.values())

    def __len__(self) -> int:
        return len(self._by_id)

    @classmethod
    def from_directory(cls, directory: Path | str) -> "ResolutionRegistry":
        files = sorted(Path(directory).glob("*.json"))
        if not files:
            raise ResolutionError(f"Nenhum arquivo .json de resolução em {directory}.")
        return cls([load_resolution_file(f) for f in files])


# --------------------------------------------------------------------------- leitura / validação
def _fail(where: str, message: str) -> ResolutionError:
    return ResolutionError(f"{where}: {message}")


def _num(where: str, data: dict, key: str, *, default: float | None = None,
         minimum: float | None = None, maximum: float | None = None, exclusive_min: bool = False) -> float:
    if key not in data:
        if default is None:
            raise _fail(where, f'falta o campo "{key}".')
        return default
    value = data[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _fail(where, f'"{key}" deve ser um número (recebido {value!r}).')
    if minimum is not None and (value <= minimum if exclusive_min else value < minimum):
        raise _fail(where, f'"{key}" deve ser {">" if exclusive_min else ">="} {minimum} (recebido {value}).')
    if maximum is not None and value > maximum:
        raise _fail(where, f'"{key}" deve ser <= {maximum} (recebido {value}).')
    return float(value)


def _check_keys(where: str, data: dict, allowed: set[str]) -> None:
    extra = sorted(set(data) - allowed)
    if extra:
        raise _fail(where, f"campo(s) desconhecido(s): {', '.join(extra)} (erro de digitação?).")


def _parse_restriction(where: str, data: Any) -> Restriction:
    if not isinstance(data, dict):
        raise _fail(where, '"restriction" deve ser um objeto.')
    _check_keys(where, data, {"scope", "factor", "cap_percent", "group", "drop_below"})
    scope = data.get("scope", "all")
    if scope not in SCOPES:
        raise _fail(where, f'"scope" deve ser um de {SCOPES} (recebido {scope!r}).')
    factor = _num(where, data, "factor", default=1.0, minimum=0, maximum=1, exclusive_min=True)
    cap = None
    if "cap_percent" in data:
        cap = _num(where, data, "cap_percent", minimum=0, maximum=100, exclusive_min=True)
    drop = _num(where, data, "drop_below", default=0.0, minimum=0)
    group = data.get("group", "")
    if not isinstance(group, str):
        raise _fail(where, '"group" deve ser texto.')
    if cap is None and factor == 1.0:
        raise _fail(where, '"restriction" não faz nada: informe "factor" menor que 1 e/ou "cap_percent".')
    return Restriction(scope=scope, factor=factor, cap_percent=cap, group=group, drop_below=drop)


def _parse_item(where: str, data: Any) -> Item:
    if not isinstance(data, dict):
        raise _fail(where, "cada item deve ser um objeto.")
    _check_keys(where, data, {"code", "label", "rule", "inputs"})
    code = data.get("code")
    if isinstance(code, bool) or not isinstance(code, int) or code <= 0:
        raise _fail(where, '"code" deve ser um inteiro maior que zero (0 é reservado para "Escolha o item...").')
    where = f"{where}, item {code}"
    label = data.get("label")
    if not isinstance(label, str) or not label.strip():
        raise _fail(where, '"label" deve ser um texto não vazio.')

    rule_data = data.get("rule")
    if not isinstance(rule_data, dict):
        raise _fail(where, 'falta o objeto "rule".')
    _check_keys(where, rule_data, {"type", "hours", "keep_presented", "restriction"})
    rtype = rule_data.get("type")
    if rtype not in RULE_TYPES:
        raise _fail(where, f'"rule.type" deve ser um de {RULE_TYPES} (recebido {rtype!r}).')
    hours = 0.0
    if rtype in ("fixed", "per_shift"):
        hours = _num(where, rule_data, "hours", minimum=0, exclusive_min=True)
    elif "hours" in rule_data:
        raise _fail(where, f'"hours" não se aplica ao tipo "{rtype}".')
    keep = rule_data.get("keep_presented", False)
    if not isinstance(keep, bool):
        raise _fail(where, '"keep_presented" deve ser true ou false.')
    if keep and rtype != "fixed":
        raise _fail(where, '"keep_presented" só se aplica ao tipo "fixed".')
    restriction = None
    if "restriction" in rule_data:
        if rtype not in ("per_shift", "presented"):
            raise _fail(where, f'"restriction" não se aplica ao tipo "{rtype}".')
        restriction = _parse_restriction(where + ", restriction", rule_data["restriction"])
        if restriction.cap_percent is not None and not restriction.group:
            restriction = Restriction(restriction.scope, restriction.factor, restriction.cap_percent,
                                      f"item{code}", restriction.drop_below)  # saldo próprio do item
    rule = Rule(type=rtype, hours=hours, keep_presented=keep, restriction=restriction)

    inputs = data.get("inputs", {})
    if not isinstance(inputs, dict):
        raise _fail(where, '"inputs" deve ser um objeto.')
    _check_keys(where + ", inputs", inputs, {"shift", "ifg", "ch"})
    shift_label = inputs.get("shift")
    if shift_label is not None and (not isinstance(shift_label, str) or not shift_label.strip()):
        raise _fail(where, '"inputs.shift" deve ser o texto do rótulo do campo (ex.: "Num. Turnos").')
    uses_ifg = inputs.get("ifg", False)
    uses_ch = inputs.get("ch", False)
    if not isinstance(uses_ifg, bool) or not isinstance(uses_ch, bool):
        raise _fail(where, '"inputs.ifg" e "inputs.ch" devem ser true ou false.')

    # Coerência: o avaliador precisa ter como informar o que a regra usa.
    if rtype == "per_shift" and not shift_label:
        raise _fail(where, 'regra "per_shift" exige "inputs.shift" (rótulo do campo de turnos).')
    if rtype == "presented" and not uses_ch:
        raise _fail(where, 'regra "presented" exige "inputs.ch": true.')
    if rtype == "fixed" and keep and not uses_ch:
        raise _fail(where, '"keep_presented" exige "inputs.ch": true (a CH apresentada é digitada).')
    if restriction is not None and restriction.scope == "non_ifg" and not uses_ifg:
        raise _fail(where, '"scope": "non_ifg" exige "inputs.ifg": true.')

    return Item(code=code, label=label.strip(), rule=rule, shift_label=shift_label,
                uses_ifg=uses_ifg, uses_ch=uses_ch)


def parse_resolution(data: Any, source: str = "resolução") -> ResolutionSpec:
    if not isinstance(data, dict):
        raise _fail(source, "o arquivo deve conter um objeto JSON.")
    _check_keys(source, data, {"id", "number", "date", "total_ch", "family", "default", "items"})
    rid = data.get("id")
    if isinstance(rid, bool) or not isinstance(rid, int) or rid < 0:
        raise _fail(source, '"id" deve ser um inteiro maior ou igual a zero.')
    number = data.get("number")
    if isinstance(number, int) and not isinstance(number, bool):
        number = str(number)
    if not isinstance(number, str) or not number.strip():
        raise _fail(source, '"number" deve ser o número da resolução (ex.: "21").')
    date = data.get("date", "")
    if not isinstance(date, str):
        raise _fail(source, '"date" deve ser texto (ex.: "15/03/2027").')
    total = _num(source, data, "total_ch", default=120.0, minimum=0, exclusive_min=True)
    family = data.get("family", str(rid))
    if not isinstance(family, str) or not family.strip():
        raise _fail(source, '"family" deve ser texto.')
    default = data.get("default", False)
    if not isinstance(default, bool):
        raise _fail(source, '"default" deve ser true ou false.')

    raw_items = data.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise _fail(source, '"items" deve ser uma lista com pelo menos um item.')
    items = [_parse_item(source, raw) for raw in raw_items]
    seen: set[int] = set()
    for item in items:
        if item.code in seen:
            raise _fail(source, f"código de item repetido: {item.code}.")
        seen.add(item.code)

    return ResolutionSpec(id=rid, number=number.strip(), date=date.strip(), total_ch=total,
                          family=family.strip(), default=default, items=tuple(items))


def load_resolution_file(path: Path | str) -> ResolutionSpec:
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ResolutionError(f"{path.name}: JSON inválido (linha {exc.lineno}, coluna {exc.colno}): {exc.msg}.") from exc
    except OSError as exc:
        raise ResolutionError(f"{path.name}: não foi possível ler o arquivo ({exc}).") from exc
    return parse_resolution(data, path.name)


@lru_cache(maxsize=1)
def default_registry() -> ResolutionRegistry:
    """Resoluções de ``data/resolutions`` (ou da pasta em ``CAAC_RESOLUTIONS_DIR``)."""
    return ResolutionRegistry.from_directory(os.environ.get("CAAC_RESOLUTIONS_DIR") or RESOLUTIONS_DIR)
