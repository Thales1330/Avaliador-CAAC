"""Geração do relatório em PDF (porte de MainFrame::GenerateReport) com ReportLab."""

from __future__ import annotations

import io
import json
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import Process
from .resolutions import ResolutionSpec
from .validation import totals, validate_activities

BASE_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = BASE_DIR / "static" / "logoIFG.png"
CONFIG_PATH = BASE_DIR / "data" / "report_config.json"

MONTHS_PT = [
    "janeiro", "fevereiro", "março", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]

_DEFAULT_CONFIG = {
    "header_lines": ["Campus Itumbiara"],
    "city": "Itumbiara/GO",
    "signatures": [],
}


def load_config() -> dict:
    try:
        with CONFIG_PATH.open(encoding="utf-8") as fh:
            return {**_DEFAULT_CONFIG, **json.load(fh)}
    except (OSError, ValueError):
        return dict(_DEFAULT_CONFIG)


def fmt_num(value: float) -> str:
    """60.0 -> '60'; 48.5 -> '48.5'."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text or "0"


def _styles() -> dict[str, ParagraphStyle]:
    return {
        "hdr": ParagraphStyle("hdr", fontName="Helvetica-Bold", fontSize=9, leading=12, alignment=TA_LEFT),
        "title1": ParagraphStyle("t1", fontName="Helvetica-Bold", fontSize=12, leading=16, spaceAfter=2),
        "title2": ParagraphStyle("t2", fontName="Helvetica-Bold", fontSize=11, leading=15, spaceAfter=10),
        "body": ParagraphStyle("body", fontName="Times-Roman", fontSize=11, leading=15,
                               alignment=TA_JUSTIFY, firstLineIndent=32),
        "center12": ParagraphStyle("c12", fontName="Times-Roman", fontSize=12, leading=16, alignment=TA_CENTER),
        "cell_l": ParagraphStyle("cl", fontName="Times-Roman", fontSize=10, leading=12, alignment=TA_LEFT),
        "cell_c": ParagraphStyle("cc", fontName="Times-Roman", fontSize=10, leading=12, alignment=TA_CENTER),
        "cell_h": ParagraphStyle("ch", fontName="Times-Bold", fontSize=10, leading=12, alignment=TA_CENTER),
        "total": ParagraphStyle("tt", fontName="Times-Bold", fontSize=12, leading=14, alignment=TA_CENTER),
        "obs_title": ParagraphStyle("ot", fontName="Times-Roman", fontSize=12, leading=16, spaceAfter=3),
        "obs": ParagraphStyle("obs", fontName="Times-Roman", fontSize=11, leading=14, leftIndent=18,
                              bulletIndent=2, alignment=TA_JUSTIFY, spaceAfter=2),
        "date": ParagraphStyle("date", fontName="Times-Roman", fontSize=12, leading=16, alignment=TA_RIGHT),
        "sig": ParagraphStyle("sig", fontName="Times-Roman", fontSize=10, leading=12, alignment=TA_CENTER),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def build_report(process: Process, spec: ResolutionSpec, today: date | None = None) -> bytes:
    """Gera o PDF do processo. As atividades são (re)validadas antes de montar o relatório."""
    today = today or date.today()
    cfg = load_config()
    st = _styles()

    validate_activities(process.activities, spec)
    total_req, total_val = totals(process.activities)

    story: list = []

    # --- cabeçalho: logo + linhas institucionais -------------------------------------------
    header_text = [Paragraph(escape(line), st["hdr"]) for line in cfg["header_lines"]]
    if LOGO_PATH.exists():
        width, height = ImageReader(str(LOGO_PATH)).getSize()
        logo_w = 55 * mm
        logo = Image(str(LOGO_PATH), width=logo_w, height=logo_w * height / width)
        header = Table([[logo, header_text]], colWidths=[62 * mm, None])
    else:
        header = Table([[header_text]])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story += [header, Spacer(1, 14)]

    story.append(_p(f"PROCESSO: N° {process.protocol}", st["title1"]))
    story.append(_p("ASSUNTO: AVALIAÇÃO DE ATIVIDADES COMPLEMENTARES", st["title2"]))

    # --- texto de abertura -----------------------------------------------------------------
    body = (
        "A Comissão de Avaliação das Atividades Complementares (CAAC) dos Cursos de Graduação do "
        "Instituto Federal de Educação, Ciência e Tecnologia de Goiás, de acordo com o Regulamento "
        f"das Atividades Complementares dos Cursos de Graduação (Resolução n° {escape(spec.legal_ref)}) "
        "e Orientações para as Atividades Complementares dos Cursos de Graduação, após analisar os "
        "certificados apresentados no presente processo, valida o cumprimento de "
        f"<b>{fmt_num(total_val)}</b> horas para o aluno <u><b>{escape(process.student_name)}</b></u>."
    )
    story.append(Paragraph(body, st["body"]))
    story.append(Spacer(1, 6))
    story.append(_p("A seguir a relação dos certificados recebidos e avaliados:", st["center12"]))
    story.append(Spacer(1, 8))

    # --- observações (iguais são agrupadas e numeradas a partir de 3) ----------------------
    shown = [a for a in process.activities if a.show_in_report]
    obs_numbers: dict[str, int] = {}
    for act in shown:
        if act.obs and act.obs not in obs_numbers:
            obs_numbers[act.obs] = len(obs_numbers) + 3

    # --- tabela de certificados ------------------------------------------------------------
    rows: list[list] = [[
        _p("EVENTO", st["cell_h"]), _p("INSTITUIÇÃO", st["cell_h"]), _p("PERÍODO", st["cell_h"]),
        _p("Carga Horária Apresentada", st["cell_h"]), _p("Carga Horária Validada", st["cell_h"]),
    ]]
    for act in shown:
        event = act.event_name + (f" - {act.event_desc}" if act.event_desc else "")
        validated = escape(fmt_num(act.ch_validated))
        if act.obs:
            validated += f"<super>{obs_numbers[act.obs]}</super>"
        rows.append([
            _p(event, st["cell_l"]),
            _p(act.institution, st["cell_c"]),
            _p(act.date, st["cell_c"]),
            _p(fmt_num(act.ch_presented), st["cell_c"]),
            Paragraph(validated, st["cell_c"]),
        ])
    rows.append([
        _p("TOTAL", st["total"]), "", "",
        _p(fmt_num(total_req), st["total"]), _p(fmt_num(total_val), st["total"]),
    ])

    table = Table(rows, colWidths=[55 * mm, 36 * mm, 24 * mm, 27.5 * mm, 27.5 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.93, 0.93, 0.93)),
        ("SPAN", (0, -1), (2, -1)),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story += [table, Spacer(1, 14)]

    # --- observações -----------------------------------------------------------------------
    notes = [
        "Os certificados analisados estão apresentados na tabela acima de acordo com a ordem de "
        "apresentação no processo.",
        f"A carga horária validada está de acordo com a Resolução n° {escape(spec.number)} do Regulamento "
        "das Atividades Complementares.",
    ] + list(obs_numbers)
    obs_block: list = [_p("Observações:", st["obs_title"])]
    for number, note in enumerate(notes, start=1):
        obs_block.append(Paragraph(escape(note), st["obs"], bulletText=f"{number}."))
    story.append(KeepTogether(obs_block))

    # --- data e assinaturas ----------------------------------------------------------------
    story.append(Spacer(1, 22))
    story.append(_p(f"{cfg['city']}, {today.day} de {MONTHS_PT[today.month - 1]} de {today.year}.", st["date"]))
    story.append(Spacer(1, 30))
    if cfg["signatures"]:
        count = len(cfg["signatures"])
        sig_table = Table(
            [[_p("_" * 18, st["sig"])] * count,
             [_p(name, st["sig"]) for name in cfg["signatures"]]],
            colWidths=[170 * mm / count] * count,
        )
        sig_table.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                       ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(KeepTogether(sig_table))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=15 * mm, bottomMargin=18 * mm,
        title=f"Avaliação de Atividades Complementares - {process.protocol}",
        author="CAAC - IFG Câmpus Itumbiara",
    )
    doc.build(story)
    return buffer.getvalue()
