"""Testes da lógica de negócio e das rotas. Rode com:  python -m pytest -q"""

from __future__ import annotations

import copy
import io
import json
import random
import shutil
import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import create_app  # noqa: E402
from caac.events import EventStore  # noqa: E402
from caac.formatting import deformat, file_stem  # noqa: E402
from caac.models import Activity, Process  # noqa: E402
from caac.report import build_report  # noqa: E402
from caac.resolutions import (  # noqa: E402
    ResolutionError,
    ResolutionRegistry,
    UnknownResolution,
    default_registry,
    load_resolution_file,
    parse_resolution,
)
from caac.validation import totals, validate_activities  # noqa: E402
from caac.xml_io import process_from_xml, process_to_xml  # noqa: E402
from legacy_validation import validate_activities as legacy_validate  # noqa: E402

REGISTRY = default_registry()
R16 = REGISTRY.get(0)
R20 = REGISTRY.get(1)


def act(item, **kw) -> Activity:
    return Activity(id=kw.pop("id", 0), item_code=item, **kw)


def expect_error(exc_type, fn, *fragments):
    """Exige que ``fn`` levante ``exc_type`` com todos os trechos na mensagem."""
    try:
        fn()
    except exc_type as exc:
        for fragment in fragments:
            assert fragment in str(exc), f"{fragment!r} não está em {str(exc)!r}"
        return
    raise AssertionError(f"{exc_type.__name__} não foi levantada")


# ----------------------------------------------------------------------------- validação
def test_fixed_items():
    acts = [act(1, shift_number=3), act(7), act(13), act(10, ch_presented=80), act(12, ch_presented=100), act(18, ch_presented=50)]
    validate_activities(acts, R16)
    assert [a.ch_validated for a in acts] == [12, 60, 30, 60, 60, 0]
    assert acts[0].ch_presented == 12 and acts[1].ch_presented == 60 and acts[2].ch_presented == 30
    assert acts[3].ch_presented == 80  # item 10 mantém a CH apresentada


def test_non_ifg_events_get_80_percent_and_cap_at_60h():
    acts = [act(3, ifg_event=False, ch_presented=50, id=1), act(3, ifg_event=False, ch_presented=50, id=2),
            act(3, ifg_event=False, ch_presented=50, id=3)]
    validate_activities(acts, R16)
    assert [a.ch_validated for a in acts] == [40, 20, 0]  # 40 + 20 = teto de 60 h
    assert all(a.limited_ch for a in acts)


def test_items_3_and_4_share_the_non_ifg_budget():
    acts = [act(3, ifg_event=False, ch_presented=50), act(4, ifg_event=False, ch_presented=50)]
    validate_activities(acts, R16)
    assert [a.ch_validated for a in acts] == [40, 20]


def test_ifg_events_are_not_reduced():
    a = act(3, ifg_event=True, ch_presented=50)
    validate_activities([a], R16)
    assert a.ch_validated == 50 and not a.limited_ch


def test_ignore_restrictions_disables_reduction_and_cap():
    a = act(3, ifg_event=False, ch_presented=100, ignore_restrictions=True)
    validate_activities([a], R16)
    assert a.ch_validated == 100


def test_courses_cap_is_40_percent_cumulative():
    acts = [act(11, ch_presented=30), act(11, ch_presented=30), act(11, ch_presented=30)]
    validate_activities(acts, R16)
    assert [a.ch_validated for a in acts] == [30, 18, 0]  # teto de 48 h
    assert [a.limited_ch for a in acts] == [False, True, True]


def test_each_capped_item_has_its_own_budget():
    acts = [act(11, ch_presented=48), act(6, ch_presented=48), act(16, ch_presented=48), act(19, ch_presented=48)]
    validate_activities(acts, R20)  # só a Res. 20 tem os itens 6, 11, 16 e 19 juntos
    assert [a.ch_validated for a in acts] == [48, 48, 48, 48]


def test_tiny_remainder_is_dropped():
    acts = [act(11, ch_presented=47.8), act(11, ch_presented=10)]
    validate_activities(acts, R16)
    assert acts[1].ch_validated == 0.0  # sobrariam 0,2 h


def test_item_17_cap_is_20_percent():
    acts = [act(17, shift_number=10), act(17, shift_number=10)]  # 20 h + 20 h
    validate_activities(acts, R16)
    assert [a.ch_validated for a in acts] == [20, 4]  # teto de 24 h
    assert acts[0].ch_presented == 20


def test_invalidated_activity_gets_zero_and_does_not_consume_budget():
    acts = [act(11, ch_presented=40, invalidate_ch=True), act(11, ch_presented=40)]
    validate_activities(acts, R16)
    assert acts[0].ch_validated == 0 and acts[0].limited_ch
    assert acts[1].ch_validated == 40


def test_order_matters_for_cumulative_limits():
    first, second = act(11, ch_presented=40), act(11, ch_presented=40)
    validate_activities([first, second], R16)
    assert (first.ch_validated, second.ch_validated) == (40, 8)
    validate_activities([second, first], R16)
    assert (second.ch_validated, first.ch_validated) == (40, 8)


def test_totals_only_count_activities_shown_in_report():
    acts = [act(7), act(7, show_in_report=False)]
    validate_activities(acts, R16)
    assert totals(acts) == (60, 60)


def test_unchosen_or_unknown_item_validates_zero():
    acts = [act(0, ch_presented=30), act(9, ch_presented=30)]  # a Res. 20 não tem o item 9
    validate_activities(acts, R20)
    assert [a.ch_validated for a in acts] == [0, 0]


def test_engine_matches_the_previous_hardcoded_implementation():
    """Resoluções 16 e 20 devem dar exatamente os mesmos resultados de antes da refatoração."""
    rng = random.Random(20261004)
    compared = limited = 0
    for spec in REGISTRY:
        codes = sorted(spec.codes)
        for _ in range(2500):
            acts = [
                Activity(
                    id=i,
                    item_code=rng.choice(codes) if rng.random() < 0.95 else 0,
                    shift_number=rng.choice([0, 1, 1, 2, 3, 5, 10, 12.5]),
                    ifg_event=rng.random() < 0.5,
                    ch_presented=rng.choice([0, 0.2, 4, 10, 17.5, 30, 40, 47.8, 48, 60, 80, 120, 200]),
                    invalidate_ch=rng.random() < 0.1,
                    ignore_restrictions=rng.random() < 0.15,
                )
                for i in range(rng.randint(1, 12))
            ]
            new, old = copy.deepcopy(acts), copy.deepcopy(acts)
            validate_activities(new, spec)
            legacy_validate(old)
            for a, b in zip(new, old):
                assert (a.ch_validated, a.ch_presented, a.limited_ch) == (b.ch_validated, b.ch_presented, b.limited_ch), \
                    f"Res. {spec.number}: divergência no item {a.item_code}: {vars(a)}"
                compared += 1
                limited += a.limited_ch
    print(f"   {compared} atividades comparadas, {limited} com CH limitada")
    assert compared > 25000 and limited > 4000  # o sorteio realmente exercita os limites


# ----------------------------------------------------------------------------- resoluções (dados)
def test_bundled_resolutions():
    assert [r.id for r in REGISTRY] == [0, 1]
    assert REGISTRY.default.id == 0
    assert R16.number == "16" and R20.number == "20" and R16.legal_ref == "16 de 26/12/2011"
    assert R16.family == R20.family and R16.total_ch == R20.total_ch == 120
    assert 17 in R16.codes and 17 not in R20.codes and 19 in R20.codes and 19 not in R16.codes
    assert len(R16.items) == 18 and len(R20.items) == 17


def test_unknown_resolution_is_an_error_not_a_fallback():
    expect_error(UnknownResolution, lambda: REGISTRY.get(7), "desconhecida", "id 7")


def valid_spec_dict() -> dict:
    return {"id": 5, "number": "21", "date": "01/01/2030", "total_ch": 100, "items": [
        {"code": 1, "label": "I - Cursos", "rule": {"type": "presented"}, "inputs": {"ch": True}},
    ]}


def _mutate(fn):
    def apply(d):
        fn(d)
        return d
    return apply


INVALID_SPECS = [
    ("sem lista de itens", _mutate(lambda d: d.pop("items")), '"items"'),
    ("lista de itens vazia", _mutate(lambda d: d.update(items=[])), '"items"'),
    ("id negativo", _mutate(lambda d: d.update(id=-1)), '"id"'),
    ("número vazio", _mutate(lambda d: d.update(number=" ")), '"number"'),
    ("total_ch zero", _mutate(lambda d: d.update(total_ch=0)), '"total_ch"'),
    ("campo desconhecido na raiz", _mutate(lambda d: d.update(totl_ch=1)), "desconhecido"),
    ("código repetido", _mutate(lambda d: d["items"].append(copy.deepcopy(d["items"][0]))), "repetido"),
    ("código zero", _mutate(lambda d: d["items"][0].update(code=0)), "maior que zero"),
    ("rótulo vazio", _mutate(lambda d: d["items"][0].update(label="")), '"label"'),
    ("tipo de regra inexistente", _mutate(lambda d: d["items"][0]["rule"].update(type="mensal")), '"rule.type"'),
    ("erro de digitação na regra", _mutate(lambda d: d["items"][0]["rule"].update(hour=4)), "desconhecido"),
    ("fixed sem hours", _mutate(lambda d: d["items"][0]["rule"].update(type="fixed")), '"hours"'),
    ("hours em presented", _mutate(lambda d: d["items"][0]["rule"].update(hours=4)), "não se aplica"),
    ("keep_presented fora de fixed", _mutate(lambda d: d["items"][0]["rule"].update(keep_presented=True)), "keep_presented"),
    ("per_shift sem campo de turnos", _mutate(lambda d: d["items"][0].update(
        rule={"type": "per_shift", "hours": 4}, inputs={})), "inputs.shift"),
    ("presented sem campo de CH", _mutate(lambda d: d["items"][0].update(inputs={})), 'inputs.ch'),
    ("non_ifg sem campo ifg", _mutate(lambda d: d["items"][0]["rule"].update(
        restriction={"scope": "non_ifg", "factor": 0.8})), "inputs.ifg"),
    ("teto acima de 100 %", _mutate(lambda d: d["items"][0]["rule"].update(
        restriction={"cap_percent": 150})), "<= 100"),
    ("fator maior que 1", _mutate(lambda d: d["items"][0]["rule"].update(
        restriction={"factor": 1.5})), '"factor"'),
    ("restrição que não faz nada", _mutate(lambda d: d["items"][0]["rule"].update(
        restriction={"scope": "all"})), "não faz nada"),
    ("escopo inexistente", _mutate(lambda d: d["items"][0]["rule"].update(
        restriction={"scope": "todos", "cap_percent": 10})), '"scope"'),
    ("número como texto", _mutate(lambda d: d["items"][0]["rule"].update(
        type="fixed", hours="60")), "número"),
]


@pytest.mark.parametrize("case", INVALID_SPECS)
def test_invalid_resolution_definitions_are_rejected(case):
    name, mutate, fragment = case
    expect_error(ResolutionError, lambda: parse_resolution(mutate(valid_spec_dict()), "nova.json"), "nova.json", fragment)


def test_valid_minimal_definition_parses():
    spec = parse_resolution(valid_spec_dict(), "nova.json")
    assert spec.id == 5 and spec.legal_ref == "21 de 01/01/2030" and spec.family == "5" and spec.total_ch == 100


def test_cap_without_group_gets_its_own_budget():
    data = valid_spec_dict()
    data["items"] = [
        {"code": 1, "label": "A", "rule": {"type": "presented", "restriction": {"cap_percent": 10}}, "inputs": {"ch": True}},
        {"code": 2, "label": "B", "rule": {"type": "presented", "restriction": {"cap_percent": 10}}, "inputs": {"ch": True}},
    ]
    spec = parse_resolution(data, "x.json")
    acts = [act(1, ch_presented=8), act(2, ch_presented=8), act(1, ch_presented=8)]  # teto de 10 h cada
    validate_activities(acts, spec)
    assert [a.ch_validated for a in acts] == [8, 8, 2]


def test_broken_json_file_reports_file_and_line(tmp_path):
    bad = tmp_path / "res99.json"
    bad.write_text('{\n  "id": 3,\n  "number": ,\n}', encoding="utf-8")
    expect_error(ResolutionError, lambda: load_resolution_file(bad), "res99.json", "JSON inválido", "linha 3")


def test_registry_rejects_duplicate_ids_and_empty_folder(tmp_path):
    a = parse_resolution({**valid_spec_dict(), "id": 3}, "a")
    b = parse_resolution({**valid_spec_dict(), "id": 3}, "b")
    expect_error(ResolutionError, lambda: ResolutionRegistry([a, b]), "repetido")
    expect_error(ResolutionError, lambda: ResolutionRegistry.from_directory(tmp_path), "Nenhum arquivo")


def test_default_resolution_rules():
    def spec(rid, default):
        return parse_resolution({**valid_spec_dict(), "id": rid, "default": default}, "x")
    assert ResolutionRegistry([spec(3, False), spec(4, False)]).default.id == 3      # nenhuma marcada: a de menor id
    assert ResolutionRegistry([spec(3, True), spec(4, False)]).default.id == 3
    assert ResolutionRegistry([spec(3, True), spec(4, True)]).default.id == 4        # várias marcadas: a mais nova


# ----------------------------------------------------------------------------- nomes de arquivo
def test_file_stem_roundtrip():
    stem = file_stem("23208.000123/2020-15", "Maria da Silva")
    assert stem == "23208-000123-2020-15[Maria-da-Silva]"
    assert deformat(stem + ".xml") == ("23208.000123/2020-15", "Maria da Silva")
    assert deformat("sem-colchetes.xml") is None


# ----------------------------------------------------------------------------- XML
def sample_process() -> Process:
    return Process(
        protocol="23208.000123/2020-15", student_name="João & <Maria> Çalves", resolution=1,
        activities=[
            Activity(id=3, item_code=11, event_name="Curso de inglês", event_desc="Nível 2", institution="IFG",
                     date="2019", ch_presented=40, obs="Certificado ilegível", ignore_restrictions=True),
            Activity(id=5, item_code=3, ifg_event=False, ch_presented=12.5, shift_number=2, show_in_report=False,
                     invalidate_ch=True),
        ],
    )


def test_xml_roundtrip_keeps_everything():
    original = sample_process()
    loaded = process_from_xml(process_to_xml(original))
    assert loaded.to_dict() == original.to_dict()


def test_xml_is_compatible_with_the_cpp_format():
    xml = process_to_xml(sample_process()).decode("utf-8")
    for tag in ("<Processo>", "<NumProtocolo>", "<NomeEstudante>", "<NumResolucao>1</NumResolucao>", '<Atividade ID="3">',
                "<DescricaoEvento>", "<EventoIFG>", "<AtividadeValida>1</AtividadeValida>", "<ExibirNoRelatorio>",
                "<IgnorarRestricoes>", "<Observacoes>"):
        assert tag in xml
    assert xml.startswith("<?xml")


def test_reads_xml_written_by_the_cpp_program():
    legacy = """<?xml version="1.0" encoding="utf-8"?>
<Processo><Nome>x</Nome><NumProtocolo>1/2</NumProtocolo><NomeEstudante>Ana</NomeEstudante>
<NumResolucao>0</NumResolucao><Atividades>
<Atividade ID="2"><Item>1</Item><Evento>Visita</Evento><NumTurnos>2.000000</NumTurnos><EventoIFG>1</EventoIFG>
<Instituicao>IFG</Instituicao><Data>10/05</Data><CH>8.000000</CH><AtividadeValida>0</AtividadeValida>
<ExibirNoRelatorio>1</ExibirNoRelatorio><IgnorarRestricoes>0</IgnorarRestricoes><Observacoes/></Atividade>
</Atividades></Processo>""".encode()
    process = process_from_xml(legacy)
    assert process.resolution == 0
    assert process.activities[0].id == 2 and process.activities[0].shift_number == 2.0
    assert process.activities[0].obs == "" and process.activities[0].show_in_report


@pytest.mark.parametrize("bad", [b"not xml", b"<Outro/>", b"<Processo><NumProtocolo>1</NumProtocolo></Processo>"])
def test_invalid_xml_is_rejected(bad):
    expect_error(ValueError, lambda: process_from_xml(bad))


# ----------------------------------------------------------------------------- PDF
def test_report_builds_a_pdf():
    process = sample_process()
    process.activities[1].show_in_report = True
    pdf = build_report(process, R20, today=date(2026, 10, 4))
    assert pdf.startswith(b"%PDF") and len(pdf) > 2000


# ----------------------------------------------------------------------------- rotas
@pytest.fixture()
def client(tmp_path):
    app = create_app(events=EventStore(tmp_path / "EventList.xml"))
    app.testing = True
    return app.test_client()


def payload():
    return {"protocol": "1/2", "student_name": "Ana", "resolution": 0, "activities": [
        {"id": 0, "item_code": 11, "ch_presented": 60},
        {"id": 1, "item_code": 9},          # existe só na Res. 16
    ]}


def test_meta_describes_every_resolution(client):
    meta = client.get("/api/meta").get_json()
    assert [(r["value"], r["label"], r["default"]) for r in meta["resolutions"]] == [
        (0, "Resolução nº 16", True), (1, "Resolução nº 20", False)]
    codes16 = [i["code"] for i in meta["items"]["0"]]
    codes20 = [i["code"] for i in meta["items"]["1"]]
    assert 17 in codes16 and 17 not in codes20 and 19 in codes20 and 19 not in codes16
    assert meta["item_fields"]["0"]["3"] == {"shift": "Num. Participações", "ifg": True, "ch": True}
    assert meta["item_fields"]["0"]["7"] == {}


def test_validate_route(client):
    data = client.post("/api/validate", json=payload()).get_json()
    assert data["activities"][0]["ch_validated"] == 48
    assert data["activities"][1]["ch_validated"] == 60
    assert data["total_validated"] == 108


def test_validate_resets_items_not_in_resolution(client):
    body = payload()
    body["resolution"] = 1  # Res. 20 não tem o item 9
    data = client.post("/api/validate", json=body).get_json()
    assert data["activities"][1]["item_code"] == 0 and data["activities"][1]["ch_validated"] == 0


def test_invalid_json_returns_400(client):
    assert client.post("/api/validate", data="nope", content_type="application/json").status_code == 400


def test_unknown_resolution_is_rejected_everywhere(client):
    body = {**payload(), "resolution": 7}
    for route in ("/api/validate", "/api/xml/export", "/api/report"):
        resp = client.post(route, json=body)
        assert resp.status_code == 400 and "desconhecida" in resp.get_json()["error"], route
    xml = process_to_xml(Process(protocol="1/2", student_name="Ana", resolution=7))
    resp = client.post("/api/xml/import", data={"file": (io.BytesIO(xml), "p.xml")})
    assert resp.status_code == 400 and "id 7" in resp.get_json()["error"]


def test_xml_export_import_roundtrip(client):
    exported = client.post("/api/xml/export", json=payload())
    assert exported.status_code == 200 and "attachment" in exported.headers["Content-Disposition"]
    back = client.post("/api/xml/import", data={"file": (io.BytesIO(exported.data), "p.xml")}).get_json()
    assert back["protocol"] == "1/2" and back["total_validated"] == 108


def test_xml_import_rejects_garbage(client):
    resp = client.post("/api/xml/import", data={"file": (io.BytesIO(b"lixo"), "p.xml")})
    assert resp.status_code == 400 and "error" in resp.get_json()


def test_report_route_returns_pdf(client):
    resp = client.post("/api/report", json=payload())
    assert resp.status_code == 200 and resp.mimetype == "application/pdf" and resp.data.startswith(b"%PDF")


def test_events_are_remembered_without_duplicates(client):
    first = client.get("/api/events").get_json()["events"]
    assert first == []
    client.post("/api/events", json={"events": ["Semana X", "Semana X", " "]})
    assert client.get("/api/events").get_json()["events"] == ["Semana X"]


def test_drive_status_without_setup_is_not_ready(client):
    assert client.get("/api/drive/status").get_json()["ready"] is False
    assert client.get("/api/drive/search?protocol=1").status_code == 502


def test_index_page_renders(client):
    html = client.get("/").get_data(as_text=True)
    assert "Avaliador CAAC" in html and "app.js" in html


# ----------------------------------------------------------------------------- uma resolução NOVA
NEW_RESOLUTION = {
    "id": 2, "number": "21", "date": "15/03/2027", "total_ch": 200, "family": "2027", "default": True,
    "items": [
        {"code": 1, "label": "I - Monitoria", "rule": {"type": "fixed", "hours": 20}},
        {"code": 2, "label": "II - Cursos",
         "rule": {"type": "presented", "restriction": {"cap_percent": 30, "group": "cursos"}},
         "inputs": {"ch": True}},
        {"code": 3, "label": "III - Eventos",
         "rule": {"type": "presented", "restriction": {"scope": "non_ifg", "factor": 0.5}},
         "inputs": {"shift": "Num. Participações", "ifg": True, "ch": True}},
        {"code": 4, "label": "IV - Projetos",
         "rule": {"type": "per_shift", "hours": 10, "restriction": {"cap_percent": 25, "group": "projetos"}},
         "inputs": {"shift": "Num. Semestres"}},
    ],
}


@pytest.fixture()
def new_resolution_client(tmp_path):
    folder = tmp_path / "resolutions"
    shutil.copytree(ROOT / "data" / "resolutions", folder)
    (folder / "res21.json").write_text(json.dumps(NEW_RESOLUTION), encoding="utf-8")
    app = create_app(events=EventStore(tmp_path / "EventList.xml"), registry=ResolutionRegistry.from_directory(folder))
    app.testing = True
    return app.test_client()


def new_payload(resolution=2):
    return {"protocol": "9/2027", "student_name": "Bia", "resolution": resolution, "activities": [
        {"id": 0, "item_code": 1},
        {"id": 1, "item_code": 2, "ch_presented": 100},                       # teto: 30 % de 200 = 60
        {"id": 2, "item_code": 2, "ch_presented": 10},                        # sem saldo
        {"id": 3, "item_code": 3, "ch_presented": 40, "ifg_event": False},    # fator 0,5
        {"id": 4, "item_code": 3, "ch_presented": 40, "ifg_event": True},     # sem restrição
        {"id": 5, "item_code": 4, "shift_number": 3},                         # 30 h
        {"id": 6, "item_code": 4, "shift_number": 3},                         # teto 25 % de 200 = 50 -> 20 h
    ]}


def test_new_resolution_needs_no_code_changes(new_resolution_client):
    client = new_resolution_client
    meta = client.get("/api/meta").get_json()
    assert [r["label"] for r in meta["resolutions"]] == ["Resolução nº 16", "Resolução nº 20", "Resolução nº 21"]
    assert [r["value"] for r in meta["resolutions"] if r["default"]] == [2]
    assert [i["label"] for i in meta["items"]["2"]][0] == "I - Monitoria"
    assert meta["item_fields"]["2"]["4"] == {"shift": "Num. Semestres"}

    data = client.post("/api/validate", json=new_payload()).get_json()
    rows = {a["id"]: a for a in data["activities"]}
    assert rows[0]["ch_validated"] == 20 and rows[0]["ch_presented"] == 20
    assert (rows[1]["ch_validated"], rows[2]["ch_validated"]) == (60, 0)
    assert rows[1]["limited_ch"] and rows[2]["limited_ch"]
    assert rows[3]["ch_validated"] == 20 and rows[3]["limited_ch"]
    assert rows[4]["ch_validated"] == 40 and not rows[4]["limited_ch"]
    assert (rows[5]["ch_presented"], rows[5]["ch_validated"]) == (30, 30)
    assert rows[6]["ch_validated"] == 20 and rows[6]["limited_ch"]
    assert data["total_validated"] == 20 + 60 + 0 + 20 + 40 + 30 + 20


def test_old_processes_keep_their_old_rules_next_to_a_new_resolution(new_resolution_client):
    client = new_resolution_client
    old = client.post("/api/validate", json=payload()).get_json()
    assert old["total_validated"] == 108  # Res. 16: curso 60 h -> 48 h, item IX = 60 h


def test_new_resolution_xml_and_pdf(new_resolution_client):
    client = new_resolution_client
    exported = client.post("/api/xml/export", json=new_payload())
    assert b"<NumResolucao>2</NumResolucao>" in exported.data
    back = client.post("/api/xml/import", data={"file": (io.BytesIO(exported.data), "p.xml")}).get_json()
    assert back["resolution"] == 2 and back["total_validated"] == 190
    pdf = client.post("/api/report", json=new_payload())
    assert pdf.status_code == 200 and pdf.data.startswith(b"%PDF")


def test_process_of_new_resolution_is_refused_by_a_program_without_it(client):
    xml = process_to_xml(Process(protocol="9/2027", student_name="Bia", resolution=2))
    resp = client.post("/api/xml/import", data={"file": (io.BytesIO(xml), "p.xml")})
    assert resp.status_code == 400 and "desconhecida" in resp.get_json()["error"]
