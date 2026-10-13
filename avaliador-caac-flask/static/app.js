"use strict";

/* Avaliador CAAC — interface. O estado do processo vive aqui; o servidor valida a
   carga horária (/api/validate), converte XML, gera o PDF e fala com o Drive. */

const $ = (sel) => document.querySelector(sel);

const state = {
  meta: null,
  process: null,        // { protocol, student_name, resolution, activities: [] }
  selected: [],         // ids das atividades selecionadas
  anchorId: null,
  nextId: 0,
  dirty: false,
  events: [],
  drive: { ready: false, credentials: false, libraries: false, authorized: false },
  validateSeq: 0,
  validateTimer: null,
};

/* ---------------------------------------------------------------- utilidades */

function fmt(n) {
  const v = Math.round((Number(n) || 0) * 100) / 100;
  return String(v);
}

let toastTimer = null;
function toast(message, isError = false) {
  const el = $("#toast");
  el.textContent = message;
  el.className = isError ? "error" : "";
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, isError ? 7000 : 3500);
}

async function api(path, options = {}) {
  const init = { ...options };
  if (init.json !== undefined) {
    init.method = init.method || "POST";
    init.headers = { "Content-Type": "application/json" };
    init.body = JSON.stringify(init.json);
    delete init.json;
  }
  let response;
  try {
    response = await fetch(path, init);
  } catch (err) {
    throw new Error("Não foi possível falar com o servidor local. Ele ainda está rodando?");
  }
  if (!response.ok) {
    let message = `Erro ${response.status}`;
    let body = null;
    try { body = await response.clone().json(); message = body.error || message; } catch (_) { /* sem JSON */ }
    const err = new Error(message);
    err.status = response.status;
    err.body = body;
    throw err;
  }
  return response;
}

async function saveBlob(response, fallbackName) {
  const disposition = response.headers.get("Content-Disposition") || "";
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  const plain = /filename="([^"]+)"/i.exec(disposition);
  const name = utf8 ? decodeURIComponent(utf8[1]) : (plain ? plain[1] : fallbackName);
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

function processForServer() {
  return { ...state.process };
}

function newActivity() {
  return {
    id: state.nextId++, item_code: 0, event_name: "", event_desc: "", shift_number: 1, ifg_event: true,
    institution: "", ch_presented: 0, date: "-", ch_validated: 0, invalidate_ch: false,
    show_in_report: true, ignore_restrictions: false, obs: "", limited_ch: false,
  };
}

const byId = (id) => state.process.activities.find((a) => a.id === id);
const fieldsFor = (act) => (state.meta.item_fields[String(state.process.resolution)] || {})[String(act.item_code)] || {};
const itemsFor = (resolution) => state.meta.items[String(resolution)] || [];
const resolutionInfo = (id) => state.meta.resolutions.find((r) => r.value === Number(id));
const defaultResolution = () => (state.meta.resolutions.find((r) => r.default) || state.meta.resolutions[0]).value;

/* Itens são códigos POR resolução. Só entre resoluções da mesma "família" o código tem o mesmo
   significado; entre famílias diferentes os itens voltam para "Escolha o item..." (nunca troca em silêncio). */
function remapItemCodes(activities, fromResolution, toResolution) {
  const from = resolutionInfo(fromResolution);
  const to = resolutionInfo(toResolution);
  const sameFamily = from && to && from.family === to.family;
  const valid = new Set(itemsFor(toResolution).map((i) => i.code));
  let reset = 0;
  for (const act of activities) {
    if (!act.item_code) continue;
    if (!sameFamily || !valid.has(act.item_code)) { act.item_code = 0; reset++; }
  }
  return reset;
}
const itemLabel = (resolution, code) => {
  const found = itemsFor(resolution).find((i) => i.code === code);
  return found ? found.label : "";
};

function markDirty(value = true) {
  state.dirty = value;
  document.title = (value ? "• " : "") + "Avaliador CAAC";
}

function confirmDiscard() {
  return !state.dirty || confirm("Existem dados não salvos. Deseja continuar e descartá-los?");
}

/* ---------------------------------------------------------------- validação (servidor) */

function scheduleValidate() {
  clearTimeout(state.validateTimer);
  state.validateTimer = setTimeout(runValidate, 120);
}

async function runValidate() {
  if (!state.process) return;
  const seq = ++state.validateSeq;
  try {
    const result = await (await api("/api/validate", { json: processForServer() })).json();
    if (seq !== state.validateSeq) return; // resposta antiga
    for (const row of result.activities) {
      const act = byId(row.id);
      if (!act) continue;
      act.item_code = row.item_code;
      act.ch_validated = row.ch_validated;
      act.limited_ch = row.limited_ch;
      // Só sobrescreve a CH apresentada quando ela é calculada (não digitada pelo usuário).
      if (!fieldsFor(act).ch) act.ch_presented = row.ch_presented;
    }
    state.totals = { requested: result.total_requested, validated: result.total_validated };
    renderGrid();
    renderTotals();
    syncFormValues();
  } catch (err) {
    toast(err.message, true);
  }
}

/* ---------------------------------------------------------------- renderização */

function render() {
  const has = !!state.process;
  $("#processBar").hidden = !has;
  $("#emptyMsg").hidden = has && state.process.activities.length > 0;
  for (const id of ["btnSave", "btnReport", "btnAdd", "btnRemove", "btnUp", "btnDown"]) $("#" + id).disabled = !has;
  $("#btnDriveSave").disabled = !has || !state.drive.ready;
  if (has) {
    $("#lblProtocol").textContent = state.process.protocol;
    $("#lblStudent").textContent = state.process.student_name;
    const info = resolutionInfo(state.process.resolution);
    $("#lblResolution").textContent = info ? info.label : `Resolução desconhecida (id ${state.process.resolution})`;
  }
  renderGrid();
  renderDetails();
  renderTotals();
}

function renderTotals() {
  const t = state.totals || { requested: 0, validated: 0 };
  $("#totReq").textContent = `Total solicitado = ${fmt(t.requested)} h`;
  $("#totVal").textContent = `Total validado = ${fmt(t.validated)} h`;
}

function cell(text, cls = "", title = "") {
  const td = document.createElement("td");
  td.textContent = text;
  if (cls) td.className = cls;
  if (title) td.title = title;
  return td;
}

function renderGrid() {
  const tbody = $("#grid tbody");
  tbody.replaceChildren();
  if (!state.process) return;
  $("#emptyMsg").hidden = state.process.activities.length > 0;

  state.process.activities.forEach((act, index) => {
    const tr = document.createElement("tr");
    tr.dataset.id = act.id;
    if (state.selected.includes(act.id)) tr.classList.add("selected");
    if (!act.show_in_report) tr.classList.add("not-shown");
    if (act.limited_ch) tr.classList.add("limited");
    if (act.ignore_restrictions) tr.classList.add("ignored");
    if (act.invalidate_ch) tr.classList.add("invalid");

    const f = fieldsFor(act);
    const label = itemLabel(state.process.resolution, act.item_code);
    tr.append(
      cell(index + 1, "num"),
      act.item_code ? cell(label, "", label) : cell("Escolha o item...", "placeholder"),
      act.event_name ? cell(act.event_name, "", act.event_name) : cell("(sem nome)", "placeholder"),
      cell(f.shift ? fmt(act.shift_number) : "-", "num"),
      cell(f.ifg ? (act.ifg_event ? "Sim" : "Não") : "-", "num"),
      cell(act.institution, "", act.institution),
      cell(act.item_code ? fmt(act.ch_presented) : "-", "num"),
      cell(act.date, "", act.date),
      cell(act.item_code ? fmt(act.ch_validated) : "-", "num"),
    );
    tbody.append(tr);
  });
}

function renderDetails() {
  const form = $("#detailsForm");
  const hint = $("#detailsHint");
  const count = state.selected.length;
  form.hidden = count !== 1;
  hint.hidden = count === 1;
  if (count === 0) hint.textContent = state.process ? "Selecione uma linha da tabela." : "Nenhum processo aberto.";
  if (count > 1) hint.textContent = `${count} linhas selecionadas. Selecione apenas uma para editar.`;
  if (count !== 1) return;

  const act = byId(state.selected[0]);
  const select = $("#fItem");
  select.replaceChildren(new Option("Escolha o item...", "0"));
  for (const item of itemsFor(state.process.resolution)) select.add(new Option(item.label, String(item.code)));

  select.value = String(act.item_code);
  $("#fEvent").value = act.event_name;
  $("#fDesc").value = act.event_desc;
  $("#fInstitution").value = act.institution;
  $("#fDate").value = act.date;
  $("#fIfg").checked = act.ifg_event;
  $("#fInvalidate").checked = act.invalidate_ch;
  $("#fIgnore").checked = act.ignore_restrictions;
  $("#fShow").checked = act.show_in_report;
  $("#fObs").value = act.obs;
  syncFormValues();
}

/* Atualiza só o que o servidor calcula, sem mexer no campo em que o usuário está digitando. */
function syncFormValues() {
  if (state.selected.length !== 1) return;
  const act = byId(state.selected[0]);
  if (!act) return;
  const f = fieldsFor(act);
  $("#fShift").disabled = !f.shift;
  $("#lblShift").textContent = f.shift || "Num. Turnos";
  $("#fCh").disabled = !f.ch;
  $("#fIfg").disabled = !f.ifg;
  if (document.activeElement !== $("#fShift")) $("#fShift").value = act.shift_number;
  if (document.activeElement !== $("#fCh")) $("#fCh").value = act.ch_presented;
  $("#fValidated").textContent = fmt(act.ch_validated);
}

/* ---------------------------------------------------------------- seleção */

$("#grid tbody").addEventListener("click", (event) => {
  const tr = event.target.closest("tr");
  if (!tr) return;
  const id = Number(tr.dataset.id);
  const ids = state.process.activities.map((a) => a.id);

  if (event.shiftKey && state.anchorId !== null) {
    const [a, b] = [ids.indexOf(state.anchorId), ids.indexOf(id)].sort((x, y) => x - y);
    state.selected = ids.slice(a, b + 1);
  } else if (event.ctrlKey || event.metaKey) {
    state.selected = state.selected.includes(id) ? state.selected.filter((x) => x !== id) : [...state.selected, id];
    state.anchorId = id;
  } else {
    state.selected = [id];
    state.anchorId = id;
  }
  renderGrid();
  renderDetails();
});

/* ---------------------------------------------------------------- edição da atividade */

function bind(selector, apply, eventName = "input") {
  $(selector).addEventListener(eventName, (event) => {
    if (state.selected.length !== 1) return;
    const act = byId(state.selected[0]);
    apply(act, event.target);
    markDirty();
    renderGrid();
    syncFormValues();
    scheduleValidate();
  });
}

bind("#fItem", (a, el) => { a.item_code = Number(el.value); }, "change");
bind("#fEvent", (a, el) => { a.event_name = el.value; });
bind("#fDesc", (a, el) => { a.event_desc = el.value; });
bind("#fShift", (a, el) => { a.shift_number = parseFloat(el.value) || 0; });
bind("#fCh", (a, el) => { a.ch_presented = parseFloat(el.value) || 0; });
bind("#fInstitution", (a, el) => { a.institution = el.value; });
bind("#fDate", (a, el) => { a.date = el.value; });
bind("#fIfg", (a, el) => { a.ifg_event = el.checked; }, "change");
bind("#fInvalidate", (a, el) => { a.invalidate_ch = el.checked; }, "change");
bind("#fIgnore", (a, el) => { a.ignore_restrictions = el.checked; }, "change");
bind("#fShow", (a, el) => { a.show_in_report = el.checked; }, "change");
bind("#fObs", (a, el) => { a.obs = el.value; });

/* ---------------------------------------------------------------- linhas */

$("#btnAdd").addEventListener("click", () => {
  const act = newActivity();
  state.process.activities.push(act);
  state.selected = [act.id];
  state.anchorId = act.id;
  markDirty();
  render();
  scheduleValidate();
  $("#fItem").focus();
});

$("#btnRemove").addEventListener("click", () => {
  if (!state.selected.length) return toast("Selecione as linhas que deseja remover.");
  if (!confirm(`Remover ${state.selected.length} atividade(s)?`)) return;
  state.process.activities = state.process.activities.filter((a) => !state.selected.includes(a.id));
  state.selected = [];
  markDirty();
  render();
  scheduleValidate();
});

function move(direction) {
  const list = state.process.activities;
  const picked = new Set(state.selected);
  const order = direction < 0 ? list.map((_, i) => i) : list.map((_, i) => i).reverse();
  for (const i of order) {
    const j = i + direction;
    if (picked.has(list[i].id) && j >= 0 && j < list.length && !picked.has(list[j].id)) {
      [list[i], list[j]] = [list[j], list[i]];
    }
  }
  markDirty();
  renderGrid();
  scheduleValidate(); // a ordem muda os limites cumulativos
}
$("#btnUp").addEventListener("click", () => move(-1));
$("#btnDown").addEventListener("click", () => move(1));

/* ---------------------------------------------------------------- processo (novo / editar) */

let processDialogMode = "new";

function openProcessDialog(mode) {
  processDialogMode = mode;
  const edit = mode === "edit";
  $("#dlgProcessTitle").textContent = edit ? "Editar processo" : "Novo processo";
  $("#pNumDocs").disabled = edit;
  $("#pProtocol").value = edit ? state.process.protocol : "";
  $("#pStudent").value = edit ? state.process.student_name : "";
  $("#pResolution").value = String(edit ? state.process.resolution : defaultResolution());
  $("#pNumDocs").value = edit ? state.process.activities.length : 1;
  $("#pError").hidden = true;
  $("#dlgProcess").showModal();
  $("#pProtocol").focus();
}

$("#btnNew").addEventListener("click", () => { if (confirmDiscard()) openProcessDialog("new"); });
$("#btnEditProcess").addEventListener("click", () => openProcessDialog("edit"));
$("#pCancel").addEventListener("click", () => $("#dlgProcess").close());

$("#formProcess").addEventListener("submit", async (event) => {
  event.preventDefault();
  const protocol = $("#pProtocol").value.trim();
  const student = $("#pStudent").value.trim();
  const resolution = Number($("#pResolution").value);
  const numDocs = parseInt($("#pNumDocs").value, 10);
  if (!protocol || !student || (processDialogMode === "new" && !(numDocs >= 0))) {
    $("#pError").textContent = "Dados incorretos! Preencha todos os campos.";
    $("#pError").hidden = false;
    return;
  }
  $("#dlgProcess").close();

  if (processDialogMode === "edit") {
    const previousResolution = state.process.resolution;
    const changed = resolution !== previousResolution;
    state.process.protocol = protocol;
    state.process.student_name = student;
    if (changed) {
      const reset = remapItemCodes(state.process.activities, previousResolution, resolution);
      if (reset) toast(`${reset} atividade(s) voltaram para "Escolha o item...": o item não existe ou não tem o mesmo significado na nova resolução.`);
    }
    state.process.resolution = resolution;
    markDirty();
    render();
    scheduleValidate();
    return;
  }

  state.nextId = 0;
  state.selected = [];
  state.totals = { requested: 0, validated: 0 };
  state.process = { protocol, student_name: student, resolution, activities: [] };

  if (state.drive.ready && confirm("Deseja buscar o aluno no Drive?\nCaso o aluno já possua processos anteriores, os comprovantes poderão ser importados.")) {
    const picked = await chooseDriveProcess("import", protocol, student);
    if (picked) await importFromDrive(picked, { protocol, student, resolution });
  }
  for (let i = 0; i < numDocs; i++) state.process.activities.push(newActivity());
  markDirty(true);
  render();
  scheduleValidate();
});

/* ---------------------------------------------------------------- arquivos XML */

$("#btnOpen").addEventListener("click", () => { if (confirmDiscard()) $("#fileInput").click(); });

$("#fileInput").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  event.target.value = "";
  if (!file) return;
  const form = new FormData();
  form.append("file", file);
  try {
    const data = await (await api("/api/xml/import", { method: "POST", body: form })).json();
    loadProcess(data);
    toast(`Processo aberto: ${file.name}`);
  } catch (err) {
    toast(`Não é possível abrir o arquivo. ${err.message}`, true);
  }
});

function loadProcess(data) {
  state.process = {
    protocol: data.protocol, student_name: data.student_name,
    resolution: data.resolution, activities: data.activities,
  };
  state.nextId = state.process.activities.reduce((m, a) => Math.max(m, a.id + 1), 0);
  state.selected = [];
  state.totals = { requested: data.total_requested, validated: data.total_validated };
  markDirty(false);
  render();
}

$("#btnSave").addEventListener("click", async () => {
  try {
    await saveBlob(await api("/api/xml/export", { json: processForServer() }), "processo.xml");
    markDirty(false);
    await rememberEvents();
  } catch (err) {
    toast(err.message, true);
  }
});

$("#btnReport").addEventListener("click", async () => {
  const incomplete = state.process.activities.filter((a) => a.show_in_report && !a.item_code).length;
  if (incomplete && !confirm(`${incomplete} atividade(s) exibida(s) no relatório ainda estão sem item. Gerar o PDF assim mesmo?`)) return;
  try {
    await saveBlob(await api("/api/report", { json: processForServer() }), "relatorio.pdf");
  } catch (err) {
    toast(err.message, true);
  }
});

/* ---------------------------------------------------------------- lista de eventos */

async function loadEvents() {
  try {
    const data = await (await api("/api/events")).json();
    state.events = data.events;
    $("#eventList").replaceChildren(...data.events.map((name) => new Option(name)));
    if (data.warning) toast(`Lista de eventos: ${data.warning}`, true);
  } catch (_) { /* o autocompletar é opcional */ }
}

async function rememberEvents() {
  const names = state.process.activities.map((a) => a.event_name.trim()).filter(Boolean);
  try {
    const data = await (await api("/api/events", { json: { events: names } })).json();
    $("#eventList").replaceChildren(...data.events.map((name) => new Option(name)));
    if (data.warning) toast(`Lista de eventos: ${data.warning}`, true);
  } catch (_) { /* não impede o salvamento */ }
}

/* ---------------------------------------------------------------- Google Drive */

async function refreshDrive() {
  try {
    state.drive = await (await api("/api/drive/status")).json();
  } catch (_) {
    state.drive = { ready: false, credentials: false, libraries: false, authorized: false };
  }
  $("#btnDriveOpen").disabled = !state.drive.ready;
  $("#btnDriveSave").disabled = !state.drive.ready || !state.process;
  const canConnect = state.drive.credentials && state.drive.libraries && !state.drive.authorized;
  $("#btnDriveConnect").hidden = !canConnect;
  const hint = !state.drive.libraries ? "Instale requirements-drive.txt para usar o Drive."
    : !state.drive.credentials ? "Coloque o credentials.json na pasta do programa para usar o Drive."
    : !state.drive.authorized ? "Clique em 'Conectar ao Drive' para autorizar." : "";
  for (const id of ["btnDriveOpen", "btnDriveSave"]) $("#" + id).title = hint;
}

$("#btnDriveConnect").addEventListener("click", async () => {
  toast("Autorize o acesso na janela do navegador que será aberta...");
  try {
    await api("/api/drive/authorize", { method: "POST" });
    await refreshDrive();
    await loadEvents();
    toast("Google Drive conectado!");
  } catch (err) {
    toast(err.message, true);
  }
});

let driveChoice = null;      // { id, name } escolhido na busca
let driveResolve = null;

function chooseDriveProcess(mode, protocol = "", student = "") {
  $("#dlgDriveTitle").textContent = mode === "import" ? "Importar comprovantes de processo anterior" : "Abrir processo do Drive";
  $("#dOk").textContent = mode === "import" ? "Importar" : "Abrir";
  $("#dProtocol").value = protocol;
  $("#dName").value = student;
  $("#dResults").replaceChildren();
  $("#dStatus").textContent = "";
  $("#dOk").disabled = true;
  driveChoice = null;
  $("#dlgDrive").showModal();
  if (protocol || student) searchDrive();
  return new Promise((resolve) => { driveResolve = resolve; });
}

function finishDriveDialog(result) {
  if ($("#dlgDrive").open) $("#dlgDrive").close();
  if (driveResolve) { driveResolve(result); driveResolve = null; }
}

async function searchDrive() {
  $("#dStatus").textContent = "Buscando arquivos no Drive...";
  $("#dResults").replaceChildren();
  $("#dOk").disabled = true;
  driveChoice = null;
  const params = new URLSearchParams({ protocol: $("#dProtocol").value, name: $("#dName").value });
  try {
    const data = await (await api(`/api/drive/search?${params}`)).json();
    $("#dStatus").textContent = data.results.length ? "" : "Nenhum processo encontrado.";
    for (const r of data.results) {
      const row = document.createElement("div");
      row.className = "result";
      row.setAttribute("role", "option");
      row.innerHTML = "<span></span><span></span>";
      row.children[0].textContent = r.protocol;
      row.children[1].textContent = r.student;
      row.addEventListener("click", () => {
        document.querySelectorAll(".result").forEach((el) => el.classList.remove("selected"));
        row.classList.add("selected");
        driveChoice = { id: r.id, name: r.name };
        $("#dOk").disabled = false;
      });
      row.addEventListener("dblclick", () => finishDriveDialog(driveChoice));
      $("#dResults").append(row);
    }
  } catch (err) {
    $("#dStatus").textContent = err.message;
  }
}

$("#dSearch").addEventListener("click", searchDrive);
$("#dCancel").addEventListener("click", () => finishDriveDialog(null));
$("#dlgDrive").addEventListener("cancel", () => finishDriveDialog(null));
$("#formDrive").addEventListener("submit", (event) => {
  event.preventDefault();
  if (driveChoice) finishDriveDialog(driveChoice);
});

/* Importa as atividades de um processo anterior para o processo novo (ficam ocultas no relatório). */
async function importFromDrive(picked, basics) {
  try {
    const data = await (await api(`/api/drive/open/${encodeURIComponent(picked.id)}`)).json();
    for (const act of data.activities) {
      act.show_in_report = false;
      state.nextId = Math.max(state.nextId, act.id + 1);
    }
    const reset = remapItemCodes(data.activities, data.resolution, basics.resolution);
    state.process.activities = data.activities;
    toast(`${data.activities.length} atividade(s) importada(s); elas ficam ocultas no relatório até você marcá-las.`
      + (reset ? ` ${reset} voltaram para "Escolha o item..." (resolução diferente).` : ""));
  } catch (err) {
    toast(`Não foi possível importar: ${err.message}`, true);
  }
}

$("#btnDriveOpen").addEventListener("click", async () => {
  if (!confirmDiscard()) return;
  const picked = await chooseDriveProcess("open");
  if (!picked) return;
  try {
    loadProcess(await (await api(`/api/drive/open/${encodeURIComponent(picked.id)}`)).json());
    toast("Processo aberto do Drive.");
  } catch (err) {
    toast(err.message, true);
  }
});

$("#btnDriveSave").addEventListener("click", async () => {
  try {
    let overwrite = false;
    for (;;) {
      try {
        const result = await (await api("/api/drive/save", { json: { ...processForServer(), overwrite } })).json();
        toast(`Salvo no Drive: ${result.name}`);
        break;
      } catch (err) {
        if (err.status === 409 && !overwrite) {
          if (!confirm("Esse arquivo já existe no Drive.\nDeseja sobrescrever?")) return;
          overwrite = true;
          continue;
        }
        throw err;
      }
    }
    markDirty(false);
    await rememberEvents();
  } catch (err) {
    toast(err.message, true);
  }
});

/* ---------------------------------------------------------------- sobre / início */

$("#btnAbout").addEventListener("click", () => $("#dlgAbout").showModal());

window.addEventListener("beforeunload", (event) => {
  if (state.dirty) { event.preventDefault(); event.returnValue = ""; }
});

async function init() {
  try {
    state.meta = await (await api("/api/meta")).json();
  } catch (err) {
    toast(err.message, true);
    return;
  }
  $("#pResolution").replaceChildren(...state.meta.resolutions.map((r) => new Option(r.label, String(r.value))));
  await Promise.all([refreshDrive(), loadEvents()]);
  render();
}

init();
