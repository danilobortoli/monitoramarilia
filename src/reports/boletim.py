"""
Boletim semanal do Observatório MATRA.

Reúne as sete coletas que terminam na data do boletim: o que entrou nos conjuntos
acompanhados (historico/mudancas), como cada regra do radar se moveu
(historico/radar.jsonl), o Diário Oficial da semana e, quando a leitura do Notion
estiver ligada, os achados registrados pela rotina DOMM. Gera um HTML no visual
do site e o converte em PDF com o WeasyPrint.

Uso: python -m src.main boletim [--fim AAAA-MM-DD]
"""

import html
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from analyzers.paineis import ROTULOS_CAMPOS, _curto
from analyzers.radar import _data, _data_br, _vazio, moeda, numero

# Rótulos das opções usadas nas bases do Notion.
ROTULOS_NOTION = {
    "grave": ("grave", "graves"), "media": ("médio", "médios"), "leve": ("leve", "leves"),
    "atencao": ("ponto de atenção", "pontos de atenção"), "LAI": ("pedido de LAI", "pedidos de LAI"),
    "oficio": ("ofício", "ofícios"), "representacao": ("representação", "representações"),
    "denuncia": ("denúncia", "denúncias"), "monitoramento": ("em monitoramento", "em monitoramento"),
}


def _contagem_notion(contagem: Dict) -> str:
    return ", ".join(_plural(v, *ROTULOS_NOTION.get(k, (k, k)))
                     for k, v in sorted(contagem.items(), key=lambda x: -x[1]))

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]
MAX_LINHAS = 12


def _plural(n: int, um: str, varios: str) -> str:
    return f"{numero(n)} {um if n == 1 else varios}"


def _periodo(inicio: date, fim: date) -> str:
    if inicio.month == fim.month:
        return f"{inicio.day} a {fim.day} de {MESES[fim.month - 1]} de {fim.year}"
    return (f"{inicio.day} de {MESES[inicio.month - 1]} a {fim.day} de "
            f"{MESES[fim.month - 1]} de {fim.year}")


# Dados

def montar(historico: Path, observatorio: Dict, fim: date) -> Dict:
    """
    Dados do boletim da semana que termina em `fim` (sete coletas: fim-6 a fim).

    Args:
        historico: Diretório historico/ (mudanças e radar.jsonl)
        observatorio: Conteúdo de docs/data/observatorio.json da última coleta
    """
    historico = Path(historico)
    inicio = fim - timedelta(days=6)

    novos = {"compra-direta": [], "contratos": [], "licitacoes": [], "obras": []}
    alterados, removidos, edicoes_novas, empenhos_novos, coletas = [], 0, [], 0, []
    for arquivo in sorted((historico / "mudancas").glob("*.json")):
        dia = _data(arquivo.stem)
        if not dia or not (inicio <= dia <= fim):
            continue
        coletas.append(dia.isoformat())
        m = json.loads(arquivo.read_text(encoding="utf-8"))
        for conjunto in novos:
            novos[conjunto].extend(m.get(conjunto, {}).get("novos", []))
            removidos += len(m.get(conjunto, {}).get("removidos", []))
        alterados.extend({"conjunto": "contratos", **a} for a in m.get("contratos", {}).get("alterados", []))
        edicoes_novas.extend(m.get("diario_oficial", {}).get("novas", []))
        empenhos_novos += len(m.get("despesas", {}).get("novos", []))

    # Radar: valor na véspera da semana (ou no primeiro dia disponível) e no fim.
    serie = []
    caminho = historico / "radar.jsonl"
    if caminho.exists():
        serie = [json.loads(l) for l in caminho.read_text(encoding="utf-8").splitlines() if l.strip()]
    antes = [l for l in serie if l["data"] < inicio.isoformat()]
    durante = [l for l in serie if inicio.isoformat() <= l["data"] <= fim.isoformat()]
    linha_inicio = antes[-1] if antes else (durante[0] if durante else None)
    linha_fim = durante[-1] if durante else None

    regras = []
    for r in observatorio.get("regras", []):
        ini = (linha_inicio or {}).get("radar", {}).get(r["id"])
        fim_ = (linha_fim or {}).get("radar", {}).get(r["id"], r["resultado"])
        regras.append({
            "n": r["n"], "regra": r["regra"], "familia": r["familia"], "fato": r.get("fato", ""),
            "unidade": r.get("unidade", ""), "inicio": ini, "fim": fim_,
            "variacao": None if ini is None else fim_ - ini,
        })

    diario = observatorio.get("diario", {})
    edicoes_semana = [e for e in diario.get("recentes", [])
                      if inicio.isoformat() <= (e.get("data") or "") <= fim.isoformat()]

    notion = observatorio.get("notion") or {}
    edicoes_notion = [e for e in notion.get("edicoes", [])
                      if inicio.isoformat() <= (e.get("data") or "") <= fim.isoformat()]

    sem_nome = [c for c in novos["contratos"] if _vazio(c.get("nomeContratada"))]
    return {
        "inicio": inicio.isoformat(),
        "fim": fim.isoformat(),
        "exercicio": observatorio.get("exercicio"),
        "coletas": coletas,
        "totais": observatorio.get("totais", {}),
        "novos": novos,
        "contratos_sem_nome": sem_nome,
        "alterados": alterados,
        "removidos": removidos,
        "edicoes_novas": edicoes_novas,
        "empenhos_novos": empenhos_novos,
        "regras": regras,
        "radar_desde": linha_inicio["data"] if linha_inicio else None,
        "diario": {"frase": diario.get("frase"), "edicoes": edicoes_semana,
                   "com_frase_ano": diario.get("com_frase"), "edicoes_ano": diario.get("edicoes")},
        "notion": {"edicoes": edicoes_notion, "achados": (notion.get("achados") or {}).get("semana")}
                  if notion else None,
    }


def resumo(b: Dict) -> str:
    """Uma frase com o que entrou na semana."""
    n = b["novos"]
    partes = [p for p in (
        _plural(len(n["compra-direta"]), "compra direta", "compras diretas") if n["compra-direta"] else "",
        (_plural(len(n["contratos"]), "contrato ou ata", "contratos ou atas")
         + (f" ({numero(len(b['contratos_sem_nome']))} sem o nome da contratada)" if b["contratos_sem_nome"] else ""))
        if n["contratos"] else "",
        _plural(len(n["licitacoes"]), "licitação", "licitações") if n["licitacoes"] else "",
        _plural(len(b["edicoes_novas"]), "edição do Diário Oficial", "edições do Diário Oficial")
        if b["edicoes_novas"] else "",
        _plural(b["empenhos_novos"], "lançamento de empenho", "lançamentos de empenho") if b["empenhos_novos"] else "",
    ) if p]
    if not b["coletas"]:
        return "Não houve coleta com histórico nesta semana."
    if not partes:
        return "Nenhum registro novo nos conjuntos acompanhados."
    if len(partes) == 1:
        return f"Entraram {partes[0]}."
    return "Entraram " + "; ".join(partes[:-1]) + " e " + partes[-1] + "."


# HTML e PDF

def _e(v) -> str:
    return html.escape(str(v if v is not None else ""))


def _variacao(v) -> str:
    if v is None:
        return "—"
    if v == 0:
        return "="
    return f"+{numero(v)}" if v > 0 else f"−{numero(-v)}"


def _tabela(cabecalho: List[str], linhas: List[List[str]], numericas=()) -> str:
    th = "".join(f'<th class="{"num" if i in numericas else ""}">{_e(c)}</th>' for i, c in enumerate(cabecalho))
    trs = "".join("<tr>" + "".join(f'<td class="{"num" if i in numericas else ""}">{c}</td>'
                                   for i, c in enumerate(l)) + "</tr>" for l in linhas)
    return f"<table><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table>"


def _mais(lista: List, mostrados: int) -> str:
    resto = len(lista) - mostrados
    return f'<p class="nota">E mais {numero(resto)} no período.</p>' if resto > 0 else ""


CSS = """
@font-face { font-family: 'ET Book'; src: url('fonts/et-book-roman.woff'); }
@font-face { font-family: 'ET Book'; font-style: italic; src: url('fonts/et-book-italic.woff'); }
@font-face { font-family: 'ET Book'; font-weight: bold; src: url('fonts/et-book-bold.woff'); }
@font-face { font-family: 'Fira Sans'; src: url('fonts/fira-sans-400.woff'); }
@font-face { font-family: 'Fira Sans'; font-weight: 500; src: url('fonts/fira-sans-500.woff'); }
@page { size: A4; margin: 20mm 18mm 20mm 18mm;
  @bottom-left { content: 'Observatório MATRA · boletim semanal'; font: 8pt 'Fira Sans', sans-serif; color: #6b6b6b; }
  @bottom-right { content: counter(page) ' de ' counter(pages); font: 8pt 'Fira Sans', sans-serif; color: #6b6b6b; } }
body { font-family: 'ET Book', Georgia, serif; font-size: 11pt; line-height: 1.45; color: #111; }
.marca { font: 500 8pt 'Fira Sans', sans-serif; letter-spacing: .12em; text-transform: uppercase; color: #1b67b2; margin: 0; }
.casa { font-style: italic; font-size: 15pt; margin: 0 0 18pt; padding-bottom: 8pt; border-bottom: 1px solid #ccc; }
h1 { font-style: italic; font-weight: normal; font-size: 26pt; line-height: 1.1; margin: 0 0 4pt; }
.periodo { font: 500 8.5pt 'Fira Sans', sans-serif; letter-spacing: .1em; text-transform: uppercase; color: #1b67b2; margin: 0 0 12pt; }
.lead { font-size: 13pt; margin: 0 0 14pt; }
.numeros { display: flex; gap: 0; border-top: 2px solid #111; border-bottom: 1px solid #ccc; margin: 0 0 18pt; padding: 8pt 0; }
.numeros div { flex: 1; padding-right: 8pt; }
.numeros .v { font-size: 20pt; line-height: 1.1; }
.numeros .r { font: 500 7pt 'Fira Sans', sans-serif; letter-spacing: .1em; text-transform: uppercase; }
.numeros .n { font-style: italic; font-size: 8.5pt; color: #666; }
h2 { font-style: italic; font-weight: normal; font-size: 17pt; margin: 18pt 0 6pt; break-after: avoid; }
.secao { font: 500 8pt 'Fira Sans', sans-serif; letter-spacing: .12em; text-transform: uppercase; color: #1b67b2; margin: 18pt 0 0; break-after: avoid; }
h3 { font: 500 8pt 'Fira Sans', sans-serif; letter-spacing: .1em; text-transform: uppercase; color: #444; margin: 12pt 0 4pt; break-after: avoid; }
table { width: 100%; border-collapse: collapse; font-size: 9.5pt; margin: 0 0 4pt; }
th { font: 500 7pt 'Fira Sans', sans-serif; letter-spacing: .08em; text-transform: uppercase; color: #666; text-align: left; border-bottom: 1px solid #111; padding: 3pt 4pt 3pt 0; }
td { border-bottom: 1px solid #e3e3e3; padding: 4pt 4pt 4pt 0; vertical-align: top; }
.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
tr { break-inside: avoid; }
.nota { font-style: italic; font-size: 9pt; color: #666; margin: 4pt 0 0; }
.fato { font-size: 9.5pt; color: #333; }
.vazio { font-style: italic; color: #666; }
footer { margin-top: 24pt; padding-top: 6pt; border-top: 1px solid #ccc; font: 7.5pt 'Fira Sans', sans-serif; color: #6b6b6b; line-height: 1.5; }
"""


def gerar_html(b: Dict) -> str:
    inicio, fim = _data(b["inicio"]), _data(b["fim"])
    t = b["totais"]
    n = b["novos"]
    partes = []

    # Números de abertura: o que entrou e o estado do radar.
    destaques = [
        (numero(len(n["compra-direta"])), "Compras diretas", "novas na semana"),
        (numero(len(n["contratos"])), "Contratos e atas", f"{numero(len(b['contratos_sem_nome']))} sem contratada"),
        (numero(len(b["edicoes_novas"])), "Edições do Diário", "publicadas na semana"),
        (numero(t.get("contratos_vigentes", 0)), "Contratos vigentes", f"de {numero(t.get('contratos', 0))} no ano"),
    ]
    numeros_html = "".join(f'<div><div class="v">{_e(v)}</div><div class="r">{_e(r)}</div>'
                           f'<div class="n">{_e(nota)}</div></div>' for v, r, nota in destaques)

    # I. O que entrou
    partes.append('<p class="secao">I. O que entrou na semana</p><h2>Registros novos nos conjuntos acompanhados</h2>')
    compras = sorted(n["compra-direta"], key=lambda c: c.get("dataPostagem") or "", reverse=True)
    partes.append("<h3>Compras diretas</h3>")
    if compras:
        partes.append(_tabela(["Data", "Modalidade e processo", "Objeto", "Situação"], [
            [_e(_data_br(c.get("dataPostagem"))), _e(f"{c.get('modalidade')} nº {c.get('numeroProcesso')}"),
             _e(_curto(c.get("titulo"), 150)), _e(c.get("situacao"))]
            for c in compras[:MAX_LINHAS]]))
        partes.append(_mais(compras, MAX_LINHAS))
    else:
        partes.append('<p class="vazio">Nenhuma compra direta nova.</p>')

    contratos = sorted(n["contratos"], key=lambda c: c.get("dataAssinatura") or "", reverse=True)
    partes.append("<h3>Contratos e atas</h3>")
    if contratos:
        partes.append(_tabela(["Assinatura", "Tipo e número", "Processo", "Contratada", "Valor"], [
            [_e(_data_br(c.get("dataAssinatura"))), _e(f"{c.get('tipo')} nº {c.get('numeroContrato')}"),
             _e(c.get("numeroProcesso")), _e(c.get("nomeContratada") or "não informada"),
             _e(moeda(float(c.get("valorContrato") or 0)))]
            for c in contratos[:MAX_LINHAS]], numericas=(4,)))
        partes.append(_mais(contratos, MAX_LINHAS))
    else:
        partes.append('<p class="vazio">Nenhum contrato ou ata novo.</p>')

    licitacoes = n["licitacoes"]
    partes.append("<h3>Licitações</h3>")
    if licitacoes:
        partes.append(_tabela(["Edital", "Modalidade", "Objeto", "Situação"], [
            [_e(l.get("numeroEdital")), _e(l.get("modalidade")), _e(_curto(l.get("titulo"), 150)),
             _e(l.get("situacao"))] for l in licitacoes[:MAX_LINHAS]]))
        partes.append(_mais(licitacoes, MAX_LINHAS))
    else:
        partes.append('<p class="vazio">Nenhuma licitação nova.</p>')

    if b["alterados"]:
        partes.append("<h3>Contratos alterados</h3>")
        partes.append(_tabela(["Contrato", "Campos alterados"], [
            [_e(f"{a['registro'].get('tipo')} nº {a['registro'].get('numeroContrato')}, processo "
                f"{a['registro'].get('numeroProcesso')}"),
             _e("; ".join(f"{ROTULOS_CAMPOS.get(campo, campo)}: {antes or '—'} → {depois or '—'}"
                          for campo, (antes, depois) in a["campos"].items()))]
            for a in b["alterados"][:MAX_LINHAS]]))
    if b["removidos"]:
        partes.append(f'<p class="nota">{_plural(b["removidos"], "registro saiu", "registros saíram")} '
                      f'dos conjuntos de dados abertos no período.</p>')

    # II. Radar
    desde = f" desde {_data_br(b['radar_desde'])}" if b["radar_desde"] else ""
    partes.append(f'<p class="secao">II. Radar</p><h2>Como cada regra se moveu{_e(desde)}</h2>')
    partes.append(_tabela(["Nº", "Regra", "Início", "Fim", "Variação"], [
        [_e(r["n"]), f"{_e(r['regra'])}<div class=\"fato\">{_e(r['fato'])}</div>",
         _e("—" if r["inicio"] is None else numero(r["inicio"])), _e(numero(r["fim"])), _e(_variacao(r["variacao"]))]
        for r in b["regras"]], numericas=(2, 3, 4)))

    # III. Diário Oficial e acompanhamento
    d = b["diario"]
    partes.append('<p class="secao">III. Diário Oficial</p><h2>Edições da semana</h2>')
    if d["edicoes"]:
        partes.append(_tabela(["Edição", "Data", "Caracteres", "CNPJs", "“Dispensa”", "Portarias", "Quebra da ordem"], [
            [_e(e["edicao"] + (" (extra)" if e.get("extra") else "")), _e(_data_br(e["data"])),
             _e(numero(e["caracteres"])), _e(e["cnpjs"]), _e(e["dispensa"]), _e(e["portarias"]),
             "Sim" if e["frase"] else "Não"] for e in d["edicoes"]], numericas=(2, 3, 4, 5)))
        partes.append(f'<p class="nota">A justificativa de quebra da ordem cronológica consta de '
                      f'{numero(d["com_frase_ano"] or 0)} das {numero(d["edicoes_ano"] or 0)} edições do ano.</p>')
    else:
        partes.append('<p class="vazio">Nenhuma edição registrada no período.</p>')

    nt = b.get("notion")
    if nt and (nt.get("edicoes") or nt.get("achados")):
        partes.append("<h3>Acompanhamento da MATRA (rotina DOMM)</h3>")
        if nt.get("edicoes"):
            partes.append(_tabela(["Edição", "Situação", "Atos", "Irregularidades"], [
                [_e(e["numero"]), _e(e["situacao"]), _e(e.get("atos") if e.get("atos") is not None else "—"),
                 _e(e.get("irregularidades") if e.get("irregularidades") is not None else "—")]
                for e in nt["edicoes"]], numericas=(2, 3)))
        a = nt.get("achados")
        if a and a.get("novos"):
            grav = _contagem_notion(a["por_gravidade"])
            acao = _contagem_notion(a["por_acao"])
            partes.append(f'<p class="fato">{_plural(a["novos"], "achado registrado", "achados registrados")} nas '
                          f'edições da semana. Por gravidade: {_e(grav)}. Por providência: {_e(acao)}.</p>')

    # Método
    partes.append('<p class="secao">Nota de método</p>')
    partes.append(
        '<p class="fato">O boletim compara as coletas diárias do Portal da Transparência de Marília e dos dados '
        'abertos do site da Prefeitura. “Entrou” quer dizer que o registro não estava na coleta anterior; um '
        'registro editado aparece como alterado. O radar aponta registros que pedem leitura, não constata '
        'irregularidade. A citação de trechos do Diário Oficial em peças sai sempre do PDF da edição.</p>')

    coletas = (f"{_plural(len(b['coletas']), 'coleta', 'coletas')} no período" if b["coletas"]
               else "sem coletas com histórico no período")
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Boletim semanal · {_e(_periodo(inicio, fim))}</title>
<style>{CSS}</style></head><body>
<p class="marca">Marília Transparente</p>
<p class="casa">Observatório</p>
<h1>Boletim semanal</h1>
<p class="periodo">{_e(_periodo(inicio, fim))} · exercício de {_e(b['exercicio'])} · {_e(coletas)}</p>
<p class="lead">{_e(resumo(b))}</p>
<div class="numeros">{numeros_html}</div>
{''.join(partes)}
<footer>Fontes: Portal da Transparência de Marília (transparencia.marilia.sp.gov.br), dados abertos do site da
Prefeitura (marilia.sp.gov.br/portal/dados-abertos) e acompanhamento da MATRA. CPFs de pessoas físicas são
mascarados. Gerado em {_e(datetime.now().strftime('%d.%m.%Y'))} · matra.org.br</footer>
</body></html>"""


def gerar_pdf(b: Dict, saida: Path, fontes: Path) -> Path:
    """
    Grava o PDF e o JSON de metadados (lido por `index-reports`) em `saida`.

    Args:
        fontes: Diretório que contém fonts/ (docs/), base para as URLs das fontes
    """
    from weasyprint import HTML

    saida = Path(saida)
    saida.mkdir(parents=True, exist_ok=True)
    nome = f"boletim-{b['fim']}"
    pdf = saida / f"{nome}.pdf"
    HTML(string=gerar_html(b), base_url=str(Path(fontes).resolve()) + "/").write_pdf(pdf)

    inicio, fim = _data(b["inicio"]), _data(b["fim"])
    meta = {
        "tipo": "boletim",
        "titulo": f"Boletim semanal · {_periodo(inicio, fim)}",
        "periodo": f"{_data_br(b['inicio'])} a {_data_br(b['fim'])}",
        "resumo": resumo(b),
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
    }
    pdf.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return pdf
