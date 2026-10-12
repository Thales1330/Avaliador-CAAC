# Avaliador CAAC (versão Python + Flask)

Software auxiliar para cálculo e geração de relatórios de avaliação de horas complementares pela
**CAAC** (Comissão para Avaliação de Atividades Complementares) — IFG, Câmpus Itumbiara.

Reescrita em Python/Flask do programa original em C++/wxWidgets
([Thales1330/Avaliador-CAAC](https://github.com/Thales1330/Avaliador-CAAC)). Os arquivos XML são
compatíveis nos dois sentidos: processos gravados pela versão C++ abrem aqui e vice-versa.

## Como rodar

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abra <http://127.0.0.1:5000>. O servidor só aceita conexões da própria máquina.

## O que o programa faz

- **Novo processo**: protocolo, nome do estudante, resolução e quantidade de documentos.
- **Tabela de atividades**: adicionar, remover e reordenar (a ordem importa: os limites são cumulativos).
- **Validação automática da carga horária** (`caac/validation.py`), com as mesmas regras da versão C++:
  4 h por turno (itens I, II, V), 60 h fixas (VII–IX, X, XI/XII), 30 h fixas (representações e órgãos),
  eventos fora do IFG a 80 % com teto de 50 % da CH total, teto de 40 % para intérprete, cursos,
  trabalho comunitário e atividade profissional, e teto de 20 % para ouvinte em defesas.
  "Invalidar CH" zera a atividade; "Ignorar restrições" desliga os limites.
  **As regras não estão no código: cada resolução é um arquivo em `data/resolutions/`** (veja abaixo).
- **Salvar / abrir XML** no mesmo formato do original.
- **Relatório em PDF** com cabeçalho do IFG, tabela de certificados, observações numeradas e assinaturas.
  Os textos institucionais e os nomes das assinaturas ficam em `data/report_config.json`.
- **Lista de eventos** com autocompletar (`data/EventList.xml`), que cresce a cada processo salvo.
- **Google Drive** (opcional): abrir/salvar processos na pasta da CAAC e importar comprovantes de
  processos anteriores do mesmo aluno.

## Adicionando uma nova resolução

As resoluções 16 e 20 são os arquivos `data/resolutions/res16.json` e `res20.json`. Para uma resolução
nova **não é preciso mexer em código**: crie mais um arquivo `.json` nessa pasta e reinicie o programa.
Ela aparece na lista de resoluções, com seus próprios itens, campos e limites. Os processos antigos
continuam sendo calculados pelas regras da resolução em que foram criados.

Se o arquivo tiver algum erro, o programa não abre e diz qual arquivo, qual item e o que corrigir.
Faça uma cópia do `res20.json` e altere:

```json
{
  "id": 2,
  "number": "21",
  "date": "15/03/2027",
  "total_ch": 120,
  "family": "2027",
  "default": true,
  "items": [
    { "code": 1, "label": "I - Visitas técnicas",
      "rule": { "type": "per_shift", "hours": 4 },
      "inputs": { "shift": "Num. Turnos" } },

    { "code": 2, "label": "II - Cursos e minicursos",
      "rule": { "type": "presented",
                "restriction": { "cap_percent": 40, "group": "cursos", "drop_below": 0.5 } },
      "inputs": { "ch": true } }
  ]
}
```

| Campo | Significado |
|---|---|
| `id` | Número gravado no XML (`<NumResolucao>`). **Único; nunca reutilize nem mude o de uma resolução já usada.** Use o próximo livre (2, 3, ...). |
| `number`, `date` | Aparecem no PDF: "Resolução n° 21 de 15/03/2027". |
| `total_ch` | CH de atividades complementares do curso; os tetos em % são calculados sobre ela. |
| `default` | `true` para que novos processos já venham nessa resolução (se várias estiverem marcadas, vale a de maior `id`). |
| `family` | Resoluções da mesma família usam **códigos de item com o mesmo significado** (é o caso da 16 e da 20). Só entre elas os itens são mantidos ao importar um processo anterior ou trocar a resolução de um processo; entre famílias diferentes os itens voltam para "Escolha o item...". Se omitido, a resolução forma uma família própria (o mais seguro). |
| `items[].code` | Código do item **dentro desta resolução** (inteiro maior que 0, único). |
| `items[].label` | Texto mostrado na lista de itens. |
| `items[].inputs` | Campos que o avaliador preenche: `"shift": "<rótulo>"` (nº de turnos/participações), `"ifg": true` (evento do IFG?), `"ch": true` (CH apresentada). |

**Tipos de regra** (`rule.type`):

| Tipo | O que faz |
|---|---|
| `fixed` | CH validada fixa (`hours`). A CH apresentada também vira `hours`, a menos que `"keep_presented": true` (então ela é digitada e mantida). |
| `per_shift` | `hours` multiplicadas pelo número informado (turnos, participações, apresentações). |
| `presented` | A CH validada parte da CH apresentada. |
| `not_scored` | Atividade não pontuada: 0 h. |

**Restrições** (`rule.restriction`, opcional em `per_shift` e `presented`): é o que o campo
"Ignorar restrições" desliga.

| Campo | Significado |
|---|---|
| `factor` | Multiplicador, por exemplo `0.8` para contar só 80 % da CH. |
| `cap_percent` | Teto cumulativo em % de `total_ch`, na ordem da tabela. O que passar é cortado. |
| `group` | Nome do saldo compartilhado: itens do mesmo `group` dividem o teto. Se omitido, cada item tem o seu. |
| `drop_below` | Sobras menores que isso (em horas) são descartadas. |
| `scope` | `"all"` (padrão) ou `"non_ifg"` (só para eventos que não são do IFG; exige `"ifg": true` em `inputs`). |

Para conferir: rode `python -m pytest -q` (os testes validam todos os arquivos da pasta) e abra o
programa, escolha a resolução nova e teste um item de cada tipo. Para usar outra pasta de resoluções,
defina `CAAC_RESOLUTIONS_DIR`.

## Google Drive (opcional)

```bash
pip install -r requirements-drive.txt
```

1. Coloque o `credentials.json` (credencial OAuth do tipo "aplicativo para computador") na pasta do projeto.
2. Rode o programa e clique em **Conectar ao Drive** (abre o navegador para o login Google).
3. A pasta usada é a da CAAC; para trocar, defina `CAAC_DRIVE_FOLDER_ID`.

`credentials.json` e `token.json` já estão no `.gitignore`: **não os envie ao GitHub**.

## Testes

```bash
pip install pytest
python -m pytest -q
```

Cobrem as regras de validação, o XML (inclusive um arquivo no formato antigo), o PDF, as rotas e o
carregamento das resoluções (arquivos inválidos, resolução nova de ponta a ponta). Um teste compara o
motor com a implementação anterior (`tests/legacy_validation.py`, congelada) em dezenas de milhares de
casos aleatórios das resoluções 16 e 20, para garantir que as regras antigas não mudaram.

## Estrutura

```
app.py                 rotas Flask
caac/models.py         atividade e processo
caac/resolutions.py    leitura e validação dos arquivos de resolução
caac/validation.py     motor de carga horária (lê as regras da resolução)
caac/xml_io.py         leitura/gravação do XML
caac/report.py         PDF (ReportLab)
caac/drive.py          Google Drive (sem processos externos)
caac/events.py         lista de eventos
templates/ static/     interface (HTML, CSS, JavaScript puro)
data/resolutions/      uma regra por resolução (res16.json, res20.json, ...)
data/                  EventList.xml e report_config.json
tests/                 testes
```

## Diferenças em relação à versão C++

- Não depende de Windows nem de `cmd.exe`/`firstRun.bat`; o Drive roda dentro do próprio Flask
  (o token fica em `token.json`, em vez de `token.pickle`).
- **Salvar XML** e **Salvar no Drive** são botões separados (antes, salvar já enviava ao Drive).
- No relatório, as observações de atividades **ocultas** não aparecem mais no rodapé.
- Atividade sem item escolhido tem 0 h validadas (antes mantinha o valor anterior).
- Corrigido o erro de digitação "emeventos" no item VI.
- Um XML de uma resolução que o programa não conhece é recusado com mensagem clara (nunca é aberto
  como se fosse outra resolução).
- A coluna "CH apresentada" da tabela mostra o valor também nos itens de CH calculada.
- Não foi portado o atalho `Shift+E` (atualizar lista de eventos); a lista é atualizada ao abrir o
  programa e a cada salvamento.

## Licença

GPL v2 ou posterior, como o projeto original (veja `LICENSE`).
