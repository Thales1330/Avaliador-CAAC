"""Nomes de arquivo para processos (porte de FormatValues).

O protocolo ``23208.000123/2020-15`` e o nome ``Maria da Silva`` viram o arquivo
``23208-000123-2020-15[Maria-da-Silva].xml`` e podem ser recuperados depois.
"""

from __future__ import annotations

import re


def format_value(value: str) -> str:
    for char in (".", "/", " "):
        value = value.replace(char, "-")
    return value


def file_stem(protocol: str, student_name: str) -> str:
    """``<protocolo>[<nome>]`` com os caracteres problemáticos trocados por ``-``."""
    return f"{format_value(protocol)}[{format_value(student_name)}]"


def safe_filename(name: str) -> str:
    """Remove caracteres inválidos em nomes de arquivo."""
    return re.sub(r'[\\:*?"<>|\r\n\t]', "-", name)


def deformat(stem: str) -> tuple[str, str] | None:
    """Inverso de :func:`file_stem`. Aceita o nome com ou sem ``.xml``."""
    if stem.lower().endswith(".xml"):
        stem = stem[:-4]
    if "[" not in stem:
        return None
    protocol, _, rest = stem.partition("[")
    name = rest.split("]", 1)[0]
    # Só os dois primeiros "-" do protocolo voltam a ser "." e "/".
    protocol = protocol.replace("-", ".", 1).replace("-", "/", 1)
    return protocol, name.replace("-", " ")
