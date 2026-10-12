"""Avaliador CAAC - interface web em Flask.

Como rodar:
    pip install -r requirements.txt
    python app.py            # abre em http://127.0.0.1:5000

O estado do processo em edição fica no navegador; o servidor só valida a carga
horária, converte de/para XML, gera o PDF e (opcionalmente) fala com o Drive.
"""

from __future__ import annotations

import os
from urllib.parse import quote

from flask import Flask, Response, jsonify, render_template, request

from caac.drive import DriveClient, DriveError
from caac.events import EventStore
from caac.formatting import file_stem, format_value, safe_filename
from caac.models import APP_VERSION, Process
from caac.report import build_report
from caac.resolutions import ResolutionError, ResolutionRegistry, ResolutionSpec, default_registry
from caac.validation import totals, validate_activities
from caac.xml_io import process_from_xml, process_to_xml

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def create_app(
    drive: DriveClient | None = None,
    events: EventStore | None = None,
    registry: ResolutionRegistry | None = None,
) -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
    app.json.ensure_ascii = False

    drive_client = drive or DriveClient()
    event_store = events or EventStore()
    resolutions = registry or default_registry()

    # ------------------------------------------------------------------ utilidades
    def error(message: str, status: int = 400):
        return jsonify({"error": message}), status

    def read_process() -> tuple[Process, ResolutionSpec]:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            raise ValueError("Requisição inválida: esperado um JSON com o processo.")
        process = Process.from_dict(data)
        spec = resolutions.get(process.resolution)  # ValueError se a resolução não existe
        for act in process.activities:
            if act.item_code and spec.item(act.item_code) is None:
                act.item_code = 0  # item inexistente nesta resolução -> volta para "escolha o item"
        validate_activities(process.activities, spec)
        return process, spec

    def process_payload(process: Process) -> dict:
        spec = resolutions.get(process.resolution)
        validate_activities(process.activities, spec)
        requested, validated = totals(process.activities)
        payload = process.to_dict()
        payload.update(total_requested=requested, total_validated=validated)
        return payload

    def download(data: bytes, filename: str, mimetype: str) -> Response:
        response = Response(data, mimetype=mimetype)
        ascii_name = safe_filename(filename).encode("ascii", "ignore").decode() or "arquivo"
        response.headers["Content-Disposition"] = (
            f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(safe_filename(filename))}"
        )
        return response

    def drive_or_none() -> DriveClient | None:
        return drive_client if drive_client.status()["ready"] else None

    # ------------------------------------------------------------------ páginas e metadados
    @app.get("/")
    def index():
        return render_template("index.html", version=APP_VERSION)

    @app.get("/api/meta")
    def meta():
        return jsonify({
            "version": APP_VERSION,
            "resolutions": [
                {"value": r.id, "label": r.label, "number": r.number, "date": r.date, "family": r.family,
                 "default": r is resolutions.default}
                for r in resolutions
            ],
            "items": {str(r.id): [{"code": i.code, "label": i.label} for i in r.items] for r in resolutions},
            "item_fields": {str(r.id): {str(i.code): i.inputs() for i in r.items} for r in resolutions},
        })

    # ------------------------------------------------------------------ cálculo
    @app.post("/api/validate")
    def api_validate():
        try:
            process, _ = read_process()
        except ValueError as exc:
            return error(str(exc))
        requested, validated = totals(process.activities)
        return jsonify({
            "activities": [
                {"id": a.id, "item_code": a.item_code, "ch_presented": a.ch_presented,
                 "ch_validated": a.ch_validated, "limited_ch": a.limited_ch}
                for a in process.activities
            ],
            "total_requested": requested,
            "total_validated": validated,
        })

    # ------------------------------------------------------------------ XML
    @app.post("/api/xml/export")
    def xml_export():
        try:
            process, _ = read_process()
        except ValueError as exc:
            return error(str(exc))
        stem = file_stem(process.protocol, process.student_name)
        return download(process_to_xml(process), f"{stem}.xml", "application/xml")

    @app.post("/api/xml/import")
    def xml_import():
        upload = request.files.get("file")
        if upload is None:
            return error("Nenhum arquivo enviado.")
        try:
            return jsonify(process_payload(process_from_xml(upload.read())))
        except ValueError as exc:
            return error(str(exc))

    # ------------------------------------------------------------------ PDF
    @app.post("/api/report")
    def report():
        try:
            process, spec = read_process()
        except ValueError as exc:
            return error(str(exc))
        pdf = build_report(process, spec)
        return download(pdf, f"{file_stem(process.protocol, process.student_name)}.pdf", "application/pdf")

    # ------------------------------------------------------------------ lista de eventos
    @app.get("/api/events")
    def events_get():
        names, warning = event_store.load(drive_or_none())
        return jsonify({"events": names, "warning": warning})

    @app.post("/api/events")
    def events_add():
        data = request.get_json(silent=True) or {}
        new = [str(e) for e in data.get("events", []) if isinstance(e, str)]
        names, warning = event_store.add(new, drive_or_none())
        return jsonify({"events": names, "warning": warning})

    # ------------------------------------------------------------------ Google Drive
    @app.get("/api/drive/status")
    def drive_status():
        return jsonify(drive_client.status())

    @app.post("/api/drive/authorize")
    def drive_authorize():
        try:
            drive_client.authorize()
        except DriveError as exc:
            return error(str(exc), 400)
        return jsonify(drive_client.status())

    @app.get("/api/drive/search")
    def drive_search():
        try:
            results = drive_client.search_processes(
                format_value(request.args.get("protocol", "").strip()),
                format_value(request.args.get("name", "").strip()),
            )
        except DriveError as exc:
            return error(str(exc), 502)
        return jsonify({"results": results})

    @app.get("/api/drive/open/<file_id>")
    def drive_open(file_id: str):
        try:
            return jsonify(process_payload(process_from_xml(drive_client.download(file_id))))
        except DriveError as exc:
            return error(str(exc), 502)
        except ValueError as exc:
            return error(str(exc))

    @app.post("/api/drive/save")
    def drive_save():
        try:
            process, _ = read_process()
        except ValueError as exc:
            return error(str(exc))
        overwrite = bool((request.get_json(silent=True) or {}).get("overwrite"))
        name = f"{file_stem(process.protocol, process.student_name)}.xml"
        try:
            existing = drive_client.find_file(name)
            if existing and not overwrite:
                return jsonify({"exists": True, "name": name}), 409
            drive_client.upload(name, process_to_xml(process), replace_id=existing)
        except DriveError as exc:
            return error(str(exc), 502)
        return jsonify({"saved": True, "name": name})

    return app


try:
    app = create_app()
except ResolutionError as exc:  # arquivo de resolução com erro: mensagem clara em vez de traceback
    raise SystemExit(f"\nERRO nos arquivos de resolução (pasta data/resolutions):\n  {exc}\n") from None

if __name__ == "__main__":
    # Servidor local de uso pessoal: só aceita conexões da própria máquina.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=bool(os.environ.get("FLASK_DEBUG")))
