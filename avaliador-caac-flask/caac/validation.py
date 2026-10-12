"""Motor de validação da carga horária.

O motor não conhece nenhum número de resolução: ele lê, para cada atividade, a regra do item
na ``ResolutionSpec`` recebida (veja ``caac/resolutions.py`` e ``data/resolutions/*.json``).

As atividades são avaliadas na ordem em que aparecem na lista, porque os limites são
cumulativos: a mesma atividade pode ser validada por inteiro, parcialmente ou zerada
dependendo do que veio antes dela.
"""

from __future__ import annotations

from typing import Iterable

from .models import Activity
from .resolutions import ResolutionSpec, Rule


def validate_activities(activities: Iterable[Activity], spec: ResolutionSpec) -> None:
    """Calcula ``ch_validated`` / ``limited_ch`` (e ajusta ``ch_presented``) no próprio objeto."""
    used: dict[str, float] = {}  # saldo já consumido de cada grupo de teto

    for act in activities:
        act.limited_ch = False

        if act.invalidate_ch:
            act.ch_validated = 0.0
            act.limited_ch = True
            continue

        item = spec.item(act.item_code)
        if item is None:  # 0 = item ainda não escolhido (ou código que não existe nesta resolução)
            act.ch_validated = 0.0
            continue

        _apply_rule(act, item.rule, spec.total_ch, used)


def _apply_rule(act: Activity, rule: Rule, total_ch: float, used: dict[str, float]) -> None:
    # 1) valor-base da atividade
    if rule.type == "not_scored":
        act.ch_validated = 0.0
        return
    if rule.type == "fixed":
        base = rule.hours
        if not rule.keep_presented:
            act.ch_presented = rule.hours
        act.ch_validated = base
        return
    if rule.type == "per_shift":
        base = act.shift_number * rule.hours
        act.ch_presented = base
    else:  # "presented"
        base = act.ch_presented

    # 2) restrições (fator de redução e/ou teto cumulativo)
    restriction = rule.restriction
    if restriction is None:
        act.ch_validated = base
        return

    ignored = act.ignore_restrictions
    if restriction.scope == "non_ifg" and (act.ifg_event or ignored):
        act.ch_validated = base  # não sofre a restrição e não consome saldo
        return

    value = base if ignored else base * restriction.factor
    old = used.get(restriction.group, 0.0)
    used[restriction.group] = old + value

    validated = value
    limited = not ignored and restriction.factor != 1.0  # sofreu redução pelo fator

    if restriction.cap_percent is not None and not ignored:
        limit = total_ch * restriction.cap_percent / 100.0
        if used[restriction.group] > limit:
            validated = max(limit - old, 0.0)
            if validated < restriction.drop_below:  # descarta "lixo" numérico muito próximo de zero
                validated = 0.0
            limited = True

    act.ch_validated = validated
    act.limited_ch = limited


def totals(activities: Iterable[Activity]) -> tuple[float, float]:
    """(total solicitado, total validado) considerando só o que aparece no relatório."""
    requested = validated = 0.0
    for act in activities:
        if act.show_in_report:
            requested += act.ch_presented
            validated += act.ch_validated
    return requested, validated
