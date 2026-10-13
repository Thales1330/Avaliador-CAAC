"""Lista de eventos usada no autocompletar (porte de EventList).

A lista fica em ``data/EventList.xml`` e, se o Drive estiver conectado, é
sincronizada com o arquivo ``EventList.xml`` da pasta da CAAC.
"""

from __future__ import annotations

import threading
import xml.etree.ElementTree as ET
from pathlib import Path

from .drive import EVENT_LIST_NAME, DriveClient, DriveError

BASE_DIR = Path(__file__).resolve().parent.parent
EVENT_LIST_PATH = BASE_DIR / "data" / "EventList.xml"


def parse_events(data: bytes) -> list[str]:
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return []
    if root.tag != "Lista":
        return []
    return [(node.text or "").strip() for node in root.findall("Evento") if (node.text or "").strip()]


def serialize_events(events: list[str]) -> bytes:
    root = ET.Element("Lista")
    for event in events:
        ET.SubElement(root, "Evento").text = event
    ET.indent(root, space="\t")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


class EventStore:
    def __init__(self, path: Path = EVENT_LIST_PATH) -> None:
        self.path = path
        self._lock = threading.Lock()

    def load_local(self) -> list[str]:
        try:
            return parse_events(self.path.read_bytes())
        except OSError:
            return []

    def _save_local(self, events: list[str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(serialize_events(events))

    def load(self, drive: DriveClient | None = None) -> tuple[list[str], str | None]:
        """Lista de eventos. Com ``drive`` pronto, baixa a versão compartilhada e a mescla à local.

        Retorna ``(eventos, aviso)``; ``aviso`` descreve uma falha de sincronização (não fatal).
        """
        with self._lock:
            events = self.load_local()
            warning = None
            if drive is not None:
                try:
                    file_id = drive.find_file(EVENT_LIST_NAME)
                    if file_id:
                        remote = parse_events(drive.download(file_id))
                        events = remote + [e for e in events if e not in remote]
                        self._save_local(events)
                except DriveError as exc:
                    warning = str(exc)
            return events, warning

    def add(self, new_events: list[str], drive: DriveClient | None = None) -> tuple[list[str], str | None]:
        """Acrescenta eventos novos (sem duplicar), grava localmente e, se possível, no Drive."""
        with self._lock:
            events = self.load_local()
            changed = False
            for name in new_events:
                name = name.strip()
                if name and name not in events:
                    events.append(name)
                    changed = True
            warning = None
            if changed:
                self._save_local(events)
                if drive is not None:
                    try:
                        drive.upload(EVENT_LIST_NAME, serialize_events(events),
                                     replace_id=drive.find_file(EVENT_LIST_NAME))
                    except DriveError as exc:
                        warning = str(exc)
            return events, warning
