"""Integração opcional com o Google Drive (substitui o antigo googleDiveAPI.py).

Funciona sem chamar processos externos: tudo roda dentro do Flask. As
bibliotecas do Google só são importadas quando o Drive é usado, então o resto
do programa funciona mesmo sem elas.

Configuração:
  * ``credentials.json`` (credenciais OAuth "aplicativo para computador") na pasta do projeto,
    ou o caminho em ``CAAC_CREDENTIALS``;
  * pasta do Drive em ``CAAC_DRIVE_FOLDER_ID`` (o padrão é a pasta usada pela CAAC).
"""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

from .formatting import deformat

BASE_DIR = Path(__file__).resolve().parent.parent
SCOPES = ["https://www.googleapis.com/auth/drive"]
DEFAULT_FOLDER_ID = "16leQlIP3Sfx4N5LJSAZtgFRYWx0xeg1O"
EVENT_LIST_NAME = "EventList.xml"


class DriveError(RuntimeError):
    """Erro de configuração, autorização ou comunicação com o Drive."""


def _q(value: str) -> str:
    """Escapa um valor para uso dentro de aspas simples numa consulta do Drive."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


class DriveClient:
    def __init__(self) -> None:
        self.folder_id = os.environ.get("CAAC_DRIVE_FOLDER_ID", DEFAULT_FOLDER_ID)
        self.credentials_path = Path(os.environ.get("CAAC_CREDENTIALS", BASE_DIR / "credentials.json"))
        self.token_path = Path(os.environ.get("CAAC_TOKEN", BASE_DIR / "token.json"))
        self._service: Any = None

    # ------------------------------------------------------------------ estado / autorização
    @staticmethod
    def libraries_installed() -> bool:
        try:
            import google.auth  # noqa: F401
            import google_auth_oauthlib  # noqa: F401
            import googleapiclient  # noqa: F401
        except ImportError:
            return False
        return True

    def status(self) -> dict[str, Any]:
        """Resumo para a interface: o que falta para o Drive funcionar."""
        installed = self.libraries_installed()
        has_credentials = self.credentials_path.exists()
        authorized = False
        if installed and self.token_path.exists():
            try:
                authorized = self._load_credentials() is not None
            except DriveError:
                authorized = False
        return {
            "libraries": installed,
            "credentials": has_credentials,
            "authorized": authorized,
            "ready": installed and authorized,
        }

    def _load_credentials(self):
        from google.auth.exceptions import RefreshError
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        if not self.token_path.exists():
            return None
        creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        if creds.valid:
            return creds
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                return None
            self.token_path.write_text(creds.to_json(), encoding="utf-8")
            return creds
        return None

    def authorize(self) -> None:
        """Abre o navegador para o login Google (bloqueia até concluir) e grava ``token.json``."""
        if not self.libraries_installed():
            raise DriveError("Instale as dependências do Drive: pip install -r requirements-drive.txt")
        if not self.credentials_path.exists():
            raise DriveError(f"Arquivo de credenciais não encontrado: {self.credentials_path.name}")
        from google_auth_oauthlib.flow import InstalledAppFlow

        flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), SCOPES)
        creds = flow.run_local_server(port=0)
        self.token_path.write_text(creds.to_json(), encoding="utf-8")
        self._service = None

    def _drive(self):
        if self._service is not None:
            return self._service
        if not self.libraries_installed():
            raise DriveError("Dependências do Google Drive não instaladas.")
        creds = self._load_credentials()
        if creds is None:
            raise DriveError("Google Drive não autorizado. Use o botão 'Conectar ao Drive'.")
        from googleapiclient.discovery import build

        self._service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return self._service

    # ------------------------------------------------------------------ operações
    def _list(self, query: str) -> list[dict[str, str]]:
        files: list[dict[str, str]] = []
        token = None
        while True:
            try:
                resp = self._drive().files().list(
                    q=query, pageSize=100, pageToken=token, fields="nextPageToken, files(id, name)"
                ).execute()
            except Exception as exc:  # erros de rede/HTTP da biblioteca do Google
                raise DriveError(f"Falha ao consultar o Drive: {exc}") from exc
            files += resp.get("files", [])
            token = resp.get("nextPageToken")
            if not token:
                return files

    def search_processes(self, formatted_protocol: str, formatted_name: str) -> list[dict[str, str]]:
        """Processos da pasta cujo nome contém o protocolo OU o nome (já no formato de arquivo)."""
        conditions = []
        for term in (formatted_protocol, formatted_name):
            if term:
                conditions.append(f"name contains '{_q(term)}'")
        if not conditions:
            query = f"'{self.folder_id}' in parents and trashed = false"
        else:
            query = f"'{self.folder_id}' in parents and ({' or '.join(conditions)}) and trashed = false"

        results = []
        for item in self._list(query):
            if item["name"] == EVENT_LIST_NAME:
                continue
            parsed = deformat(item["name"])
            if parsed:
                results.append({"id": item["id"], "name": item["name"],
                                "protocol": parsed[0], "student": parsed[1]})
        return sorted(results, key=lambda r: (r["student"].lower(), r["protocol"]))

    def find_file(self, name: str) -> str | None:
        """ID do arquivo com este nome exato na pasta (ou ``None``)."""
        found = self._list(f"'{self.folder_id}' in parents and name = '{_q(name)}' and trashed = false")
        return found[0]["id"] if found else None

    def download(self, file_id: str) -> bytes:
        from googleapiclient.http import MediaIoBaseDownload

        try:
            request = self._drive().files().get_media(fileId=file_id)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
        except Exception as exc:
            raise DriveError(f"Falha ao baixar o arquivo: {exc}") from exc
        return buffer.getvalue()

    def upload(self, name: str, data: bytes, replace_id: str | None = None) -> str:
        """Grava ``data`` na pasta. Se ``replace_id`` for dado, o arquivo antigo é atualizado no lugar."""
        from googleapiclient.http import MediaIoBaseUpload

        media = MediaIoBaseUpload(io.BytesIO(data), mimetype="text/xml", resumable=False)
        try:
            if replace_id:
                result = self._drive().files().update(fileId=replace_id, media_body=media, fields="id").execute()
            else:
                body = {"name": name, "parents": [self.folder_id]}
                result = self._drive().files().create(body=body, media_body=media, fields="id").execute()
        except Exception as exc:
            raise DriveError(f"Falha ao gravar no Drive: {exc}") from exc
        return result["id"]
