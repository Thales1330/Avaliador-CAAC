"""Leitura e gravação do processo em XML (mesmo formato do programa original).

Os arquivos gravados pela versão C++ continuam abrindo aqui e vice-versa.
Atenção ao nome histórico da tag ``<AtividadeValida>``: ela guarda o flag
"invalidar CH" (1 = atividade invalidada).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from .formatting import file_stem
from .models import Activity, Process


def _num(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


def process_to_xml(process: Process) -> bytes:
    root = ET.Element("Processo")
    ET.SubElement(root, "Nome").text = file_stem(process.protocol, process.student_name)
    ET.SubElement(root, "NumProtocolo").text = process.protocol
    ET.SubElement(root, "NomeEstudante").text = process.student_name
    ET.SubElement(root, "NumResolucao").text = str(process.resolution)

    activities = ET.SubElement(root, "Atividades")
    for act in process.activities:
        node = ET.SubElement(activities, "Atividade", ID=str(act.id))
        ET.SubElement(node, "Item").text = str(act.item_code)
        ET.SubElement(node, "Evento").text = act.event_name
        ET.SubElement(node, "DescricaoEvento").text = act.event_desc
        ET.SubElement(node, "NumTurnos").text = _num(act.shift_number)
        ET.SubElement(node, "EventoIFG").text = str(int(act.ifg_event))
        ET.SubElement(node, "Instituicao").text = act.institution
        ET.SubElement(node, "Data").text = act.date
        ET.SubElement(node, "CH").text = _num(act.ch_presented)
        ET.SubElement(node, "AtividadeValida").text = str(int(act.invalidate_ch))
        ET.SubElement(node, "ExibirNoRelatorio").text = str(int(act.show_in_report))
        ET.SubElement(node, "IgnorarRestricoes").text = str(int(act.ignore_restrictions))
        ET.SubElement(node, "Observacoes").text = act.obs

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _text(node: ET.Element | None, tag: str, default: str = "") -> str:
    child = node.find(tag) if node is not None else None
    return (child.text or "") if child is not None else default


def _float(node: ET.Element, tag: str, default: float = 0.0) -> float:
    try:
        return float(_text(node, tag, str(default)).strip().replace(",", "."))
    except ValueError:
        return default


def _int(node: ET.Element, tag: str, default: int = 0) -> int:
    return int(_float(node, tag, float(default)))


def process_from_xml(data: bytes) -> Process:
    """Interpreta um XML de processo. Levanta ``ValueError`` se o arquivo não for válido."""
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        raise ValueError(f"XML inválido: {exc}") from exc

    if root.tag != "Processo":
        raise ValueError("O arquivo não é um processo do Avaliador CAAC (falta a tag <Processo>).")
    if root.find("NumProtocolo") is None or root.find("NomeEstudante") is None:
        raise ValueError("O arquivo não contém o número do protocolo ou o nome do estudante.")
    activities_node = root.find("Atividades")
    if activities_node is None:
        raise ValueError("O arquivo não contém a lista de atividades.")

    # O id da resolução é validado por quem chama (ResolutionRegistry.get): um id desconhecido deve
    # virar erro, nunca ser trocado em silêncio por outra resolução.
    process = Process(
        protocol=_text(root, "NumProtocolo").strip(),
        student_name=_text(root, "NomeEstudante").strip(),
        resolution=_int(root, "NumResolucao"),
    )

    for index, node in enumerate(activities_node.findall("Atividade")):
        try:
            act_id = int(node.get("ID", index))
        except ValueError:
            act_id = index
        process.activities.append(
            Activity(
                id=act_id,
                item_code=_int(node, "Item"),
                event_name=_text(node, "Evento"),
                event_desc=_text(node, "DescricaoEvento"),
                shift_number=_float(node, "NumTurnos", 1.0),
                ifg_event=bool(_int(node, "EventoIFG", 1)),
                institution=_text(node, "Instituicao"),
                date=_text(node, "Data", "-"),
                ch_presented=_float(node, "CH"),
                invalidate_ch=bool(_int(node, "AtividadeValida")),
                show_in_report=bool(_int(node, "ExibirNoRelatorio", 1)),
                ignore_restrictions=bool(_int(node, "IgnorarRestricoes")),
                obs=_text(node, "Observacoes"),
            )
        )
    return process
