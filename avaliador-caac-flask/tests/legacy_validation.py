"""CÓPIA CONGELADA da validação anterior à refatoração (regras fixas no código).

Só serve de referência: tests/test_caac.py compara o motor novo (baseado em dados) com esta
versão em milhares de casos aleatórios das resoluções 16 e 20. Não é usada pelo programa.

Original: porte de MainFrame::ValidateCH.

As atividades são avaliadas na ordem em que aparecem na lista, porque os
limites são cumulativos: a mesma atividade pode ser validada por inteiro,
parcialmente ou zerada dependendo do que veio antes dela.

Limites (sobre a CH de atividades complementares, 120 h por padrão):
  * itens 3 e 4 em eventos que NÃO são do IFG: 80 % da CH apresentada, até 50 %
    do total acumulado;
  * itens 6, 11, 16 e 19: até 40 % do total, cada item separadamente;
  * item 17: até 20 % do total.
"Ignorar restrições" desliga esses limites para a atividade.
"""

from __future__ import annotations

from typing import Iterable

from caac.models import Activity

COMP_ACTIVITY_CH = 120.0


def validate_activities(activities: Iterable[Activity], comp_ch: float = COMP_ACTIVITY_CH) -> None:
    """Calcula ``ch_validated`` / ``limited_ch`` (e ajusta ``ch_presented``) no próprio objeto."""
    ch_language = 0.0   # item 6
    ch_courses = 0.0    # item 11
    ch_community = 0.0  # item 16
    ch_professional = 0.0  # item 19
    ch_tcc = 0.0        # item 17
    ch_event_non_ifg = 0.0  # itens 3 e 4 fora do IFG

    for act in activities:
        act.limited_ch = False

        if act.invalidate_ch:
            act.ch_validated = 0.0
            act.limited_ch = True
            continue

        code = act.item_code

        if code in (1, 2, 5):
            # 4 h por turno / apresentação
            act.ch_presented = act.shift_number * 4.0
            act.ch_validated = act.ch_presented

        elif code in (3, 4):
            ch = act.ch_presented
            if not act.ifg_event and not act.ignore_restrictions:
                ch *= 0.8
                old = ch_event_non_ifg
                ch_event_non_ifg += ch
                limit = comp_ch * 0.5
                if ch_event_non_ifg > limit:
                    act.ch_validated = max(limit - old, 0.0)
                else:
                    act.ch_validated = ch
                act.limited_ch = True  # (mesmo dentro do limite houve redução de 20 %)
            else:
                act.ch_validated = ch

        elif code in (6, 11, 16, 19):
            ch = act.ch_presented
            if code == 6:
                old, ch_language = ch_language, ch_language + ch
                acc = ch_language
            elif code == 11:
                old, ch_courses = ch_courses, ch_courses + ch
                acc = ch_courses
            elif code == 16:
                old, ch_community = ch_community, ch_community + ch
                acc = ch_community
            else:
                old, ch_professional = ch_professional, ch_professional + ch
                acc = ch_professional

            limit = comp_ch * 0.4
            if acc > limit and not act.ignore_restrictions:
                partial = limit - old
                if partial > 0:
                    if partial < 0.5:  # descarta "lixo" numérico muito próximo de zero
                        partial = 0.0
                    act.ch_validated = partial
                else:
                    act.ch_validated = 0.0
                act.limited_ch = True
            else:
                act.ch_validated = ch

        elif code in (7, 8, 9):
            act.ch_presented = 60.0
            act.ch_validated = 60.0

        elif code == 10:
            act.ch_validated = 60.0  # a CH apresentada é mantida

        elif code == 12:
            act.ch_validated = 60.0  # a CH apresentada é mantida

        elif code in (13, 14, 15):
            act.ch_presented = 30.0
            act.ch_validated = 30.0

        elif code == 17:
            ch = act.shift_number * 2.0
            act.ch_presented = ch
            old, ch_tcc = ch_tcc, ch_tcc + ch
            limit = comp_ch * 0.2
            if ch_tcc > limit and not act.ignore_restrictions:
                act.ch_validated = max(limit - old, 0.0)
                act.limited_ch = True
            else:
                act.ch_validated = ch

        elif code == 18:
            act.ch_validated = 0.0  # atividade não pontuada

        else:  # 0 = item ainda não escolhido
            act.ch_validated = 0.0


def totals(activities: Iterable[Activity]) -> tuple[float, float]:
    """(total solicitado, total validado) considerando só o que aparece no relatório."""
    requested = validated = 0.0
    for act in activities:
        if act.show_in_report:
            requested += act.ch_presented
            validated += act.ch_validated
    return requested, validated
