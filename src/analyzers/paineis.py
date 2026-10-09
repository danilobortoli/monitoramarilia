"""
Dados das páginas do Observatório que não são regras do radar.

- novidades: o que entrou ou mudou desde a coleta anterior (painel do dia)
- serie_contratacao_direta: dispensa e inexigibilidade sobre o empenhado, por ano
- diario: contagens sobre o texto integral das edições do ano
- transparencia: campos vazios e seções sem dado

Todas as funções recebem registros já coletados e não acessam a rede.
"""

import re
from collections import Counter
from typing import Dict, List, Optional

from collectors.portal_marilia import parse_valor
from analyzers.radar import _data, _data_br, _vazio, chave_fornecedor, moeda, numero

MAX_NOVIDADES = 5

SITUACAO_LICITACAO = {"Aberto": "aberta", "Homologado": "homologada", "Suspenso": "suspensa",
                      "Revogado": "revogada", "Anulado": "anulada", "Adjudicado": "adjudicada"}


def _curto(texto: str, limite: int = 110) -> str:
    texto = re.sub(r"\s+", " ", texto or "").strip()
    if len(texto) <= limite:
        return texto
    return texto[:limite].rsplit(" ", 1)[0].rstrip(",;:.") + "…"


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{numero(n)} {singular if n == 1 else plural}"


# Painel do dia

def novidades(
    mudancas: Optional[Dict],
    compras: List[Dict],
    contratos: List[Dict],
    licitacoes: List[Dict],
    edicoes: List[Dict],
    despesas: List[Dict],
    frase_diario: str,
) -> Dict:
    """
    Registros que pedem leitura no painel do dia.

    Sem coleta anterior (mudancas=None), usa como linha de base os registros com a
    data mais recente de cada conjunto.

    Returns:
        {"linha_de_base": bool, "resumo": str, "itens": [{tipo, titulo, detalhe, fonte, acao, link}]}
    """
    linha_de_base = mudancas is None
    if linha_de_base:
        def mais_recentes(lista, campo):
            datas = [str(r.get(campo) or "")[:10] for r in lista]
            ultima = max(datas, default="")
            return [r for r, d in zip(lista, datas) if ultima and d == ultima]

        novas_compras = mais_recentes(compras, "dataPostagem")
        novos_contratos = mais_recentes(contratos, "dataAssinatura")
        novas_licitacoes = [l for l in licitacoes if l.get("situacao") == "Aberto"]
        novas_edicoes = sorted(edicoes, key=lambda e: e.get("data") or "")[-1:]
        novas_despesas = []
        alterados = []
    else:
        novas_compras = mudancas["compra-direta"]["novos"]
        novos_contratos = mudancas["contratos"]["novos"]
        novas_licitacoes = mudancas["licitacoes"]["novos"]
        novas_edicoes = [e for e in edicoes if e.get("edicao") in set(mudancas["diario_oficial"]["novas"])]
        ids = set(mudancas["despesas"]["novos"])
        novas_despesas = [d for d in despesas if d.get("ID") in ids]
        alterados = mudancas["contratos"]["alterados"]

    itens = []

    for c in sorted(novas_compras, key=lambda c: c.get("dataPostagem") or "", reverse=True)[:2]:
        detalhe = f"Situação: {(c.get('situacao') or 'não informada').lower()}."
        if _vazio(c.get("valorEstimado")):
            detalhe += " O registro não informa valor estimado."
        itens.append({
            "tipo": f"Compra direta · {_data_br(c.get('dataPostagem'))}",
            "titulo": f"{c.get('modalidade')} nº {c.get('numeroProcesso')}: {_curto(c.get('titulo'))}",
            "detalhe": detalhe,
            "fonte": "Dados abertos · compra direta",
            "acao": "Ver no radar", "link": "radar.html",
        })

    sem_nome = [c for c in novos_contratos if _vazio(c.get("nomeContratada"))]
    if sem_nome:
        numeros = sorted({str(c.get("numeroContrato")) for c in sem_nome}, key=lambda n: (len(n), n))
        processos = sorted({str(c.get("numeroProcesso")) for c in sem_nome})
        soma = sum(float(c.get("valorContrato") or 0) for c in sem_nome)
        datas = sorted({_data_br(c.get("dataAssinatura")) for c in sem_nome})
        itens.append({
            "tipo": f"Contratos · {datas[-1] if datas else ''}",
            "titulo": f"{_plural(len(sem_nome), 'contrato ou ata', 'contratos ou atas')} sem o nome da contratada",
            "detalhe": (
                f"Nº {', '.join(numeros[:6])}{'…' if len(numeros) > 6 else ''}; "
                f"{'processo' if len(processos) == 1 else 'processos'} {', '.join(processos[:4])}. "
                f"Somam {moeda(soma)}."
            ),
            "fonte": "Dados abertos · contratos",
            "acao": "Ver no radar", "link": "radar.html",
        })

    frase = frase_diario.lower()
    com_frase = [e for e in edicoes if frase in (e.get("descricao") or "").lower()]
    for e in novas_edicoes:
        if frase in (e.get("descricao") or "").lower():
            itens.append({
                "tipo": f"Diário Oficial · edição {e.get('edicao')}",
                "titulo": "Justificativa de quebra da ordem cronológica de pagamentos",
                "detalhe": (
                    f"Invoca o art. 141, §1º, III e V, da Lei 14.133/2021. A mesma frase consta de "
                    f"{numero(len(com_frase))} das {numero(len(edicoes))} edições do ano."
                ),
                "fonte": "Dados abertos · diário oficial",
                "acao": "Ler a edição", "link": "diario.html",
            })

    for l in sorted(novas_licitacoes, key=lambda l: l.get("dataRealizacao") or "", reverse=True)[:1]:
        detalhe = f"{l.get('modalidade')}."
        if _vazio(l.get("valorEstimado")):
            detalhe += " O conjunto de dados não traz valor estimado."
        itens.append({
            "tipo": f"Licitação · {SITUACAO_LICITACAO.get(l.get('situacao'), (l.get('situacao') or '').lower())}",
            "titulo": f"Edital {l.get('numeroEdital')}: {_curto(l.get('titulo'))}",
            "detalhe": detalhe,
            "fonte": "Dados abertos · licitações",
            "acao": "Ver lacunas", "link": "transparencia.html",
        })

    # Empenhos novos de maior valor, só de pessoas jurídicas.
    empenhos = [
        d for d in novas_despesas
        if d.get("TipEmpenho") == "Empenho" and not chave_fornecedor(d.get("CNPJ")).startswith("cpf:")
    ]
    for d in sorted(empenhos, key=lambda d: parse_valor(d.get("ValorEmpenhado")), reverse=True)[:1]:
        itens.append({
            "tipo": f"Empenho · {_data_br(d.get('DataMovEmp'))}",
            "titulo": f"Empenho nº {d.get('NroEmpenho')} a {(d.get('NomeFornecedor') or '').strip()}",
            "detalhe": f"{moeda(parse_valor(d.get('ValorEmpenhado')))}, {(d.get('UG') or '').strip().lower()}.",
            "fonte": "Portal · despesas e investimentos",
            "acao": "Ver no radar", "link": "radar.html",
        })

    for a in alterados[:1]:
        r = a["registro"]
        campos = ", ".join(a["campos"])
        itens.append({
            "tipo": f"Contratos · alterado",
            "titulo": f"{r.get('tipo')} nº {r.get('numeroContrato')}, processo {r.get('numeroProcesso')}",
            "detalhe": f"Campos alterados desde a coleta anterior: {campos}.",
            "fonte": "Dados abertos · contratos",
            "acao": "Ver no radar", "link": "radar.html",
        })

    itens = itens[:MAX_NOVIDADES]
    for n, item in enumerate(itens, 1):
        item["n"] = str(n)

    # O resumo continua a frase "Na coleta de hoje," que abre o painel.
    if linha_de_base:
        resumo = ("que abre o histórico do Observatório, entram abaixo os registros mais recentes "
                  "de cada conjunto. A partir da próxima coleta, o painel mostra só o que mudou.")
    else:
        partes = [
            _plural(len(novas_compras), "compra direta nova", "compras diretas novas") if novas_compras else "",
            (_plural(len(novos_contratos), "contrato ou ata novo", "contratos ou atas novos")
             + (f", {numero(len(sem_nome))} sem o nome da contratada" if sem_nome else "")) if novos_contratos else "",
            _plural(len(novas_licitacoes), "licitação nova", "licitações novas") if novas_licitacoes else "",
            _plural(len(novas_edicoes), "edição do Diário Oficial", "edições do Diário Oficial") if novas_edicoes else "",
            _plural(len(empenhos), "empenho novo", "empenhos novos") if empenhos else "",
            _plural(len(alterados), "contrato alterado", "contratos alterados") if alterados else "",
        ]
        partes = [p for p in partes if p]
        if not partes:
            resumo = "nenhum registro novo nos conjuntos acompanhados."
        elif len(partes) == 1:
            resumo = f"entrou {partes[0]}." if partes[0].startswith("1 ") else f"entraram {partes[0]}."
        else:
            resumo = "entraram " + "; ".join(partes[:-1]) + " e " + partes[-1] + "."
    return {"linha_de_base": linha_de_base, "resumo": resumo, "itens": itens}


# Série de contratação direta

MODALIDADES_DIRETAS = ("DISPENSA", "DISPENSADA", "INEXIGIBILIDADE")


def serie_contratacao_direta(por_ano: Dict[int, List[Dict]]) -> List[Dict]:
    """
    Dispensa e inexigibilidade sobre o empenhado, a partir de 'Empenho por Modalidade'.

    Args:
        por_ano: {exercício: registros da visão}
    """
    serie = []
    for ano, linhas in sorted(por_ano.items()):
        total = direta = sem_modalidade = 0.0
        for l in linhas:
            modalidade = (l.get("tipoLic") or "").strip().upper()
            valor = parse_valor(l.get("ValorEmpenhado"))
            total += valor
            if modalidade in MODALIDADES_DIRETAS:
                direta += valor
            elif modalidade.startswith("OUTROS"):
                sem_modalidade += valor
        if total > 0:
            serie.append({
                "ano": ano,
                "direta": round(direta, 2),
                "total": round(total, 2),
                "pct_direta": round(100 * direta / total, 1),
                "pct_sem_modalidade": round(100 * sem_modalidade / total, 1),
            })
    return serie


# Diário Oficial

_CNPJ = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
_DISPENSA = re.compile(r"dispensa", re.IGNORECASE)
_PORTARIA = re.compile(r"PORTARIA N[ÚU]MERO")
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def diario(edicoes: List[Dict], frase: str, recentes: int = 7) -> Dict:
    """Contagens sobre o texto integral das edições do ano."""
    alvo = frase.lower()
    ordenadas = sorted(edicoes, key=lambda e: e.get("data") or "")
    tem = [alvo in (e.get("descricao") or "").lower() for e in ordenadas]

    meses = Counter()
    com = Counter()
    for e, t in zip(ordenadas, tem):
        d = _data(e.get("data"))
        if d:
            meses[d.month] += 1
            com[d.month] += int(t)

    tabela = []
    for e, t in list(zip(ordenadas, tem))[-recentes:][::-1]:
        texto = e.get("descricao") or ""
        tabela.append({
            "edicao": e.get("edicao"),
            "data": (e.get("data") or "")[:10],
            "extra": bool(e.get("edicaoExtra")),
            "caracteres": len(texto),
            "cnpjs": len(set(_CNPJ.findall(texto))),
            "dispensa": len(_DISPENSA.findall(texto)),
            "portarias": len(_PORTARIA.findall(texto)),
            "frase": t,
        })

    # Trecho da edição mais recente que traz a frase: a frase e o parágrafo seguinte.
    trecho = None
    for e, t in zip(reversed(ordenadas), reversed(tem)):
        if t:
            texto = e.get("descricao") or ""
            i = texto.lower().find(alvo)
            antes = texto[:i].rstrip().split("\n")[-1].strip()
            depois = texto[i + len(frase):].split("\n")
            trecho = {
                "edicao": e.get("edicao"),
                "data": (e.get("data") or "")[:10],
                "antes": antes,
                "frase": texto[i:i + len(frase)],
                "depois": _curto(depois[0], 160),
                "seguinte": _curto(" ".join(p.strip() for p in depois[1:3] if p.strip()), 160),
            }
            break

    primeira = next((e for e, t in zip(ordenadas, tem) if t), None)
    return {
        "frase": frase,
        "edicoes": len(ordenadas),
        "extras": sum(1 for e in ordenadas if e.get("edicaoExtra")),
        "com_frase": sum(tem),
        "primeira_edicao": ordenadas[0].get("edicao") if ordenadas else None,
        "primeira_data": (ordenadas[0].get("data") or "")[:10] if ordenadas else None,
        "ultima_edicao": ordenadas[-1].get("edicao") if ordenadas else None,
        "ultima_data": (ordenadas[-1].get("data") or "")[:10] if ordenadas else None,
        "primeira_com_frase": primeira.get("edicao") if primeira else None,
        "faixa": [int(t) for t in tem],
        "meses": [{"mes": MESES[m - 1], "com": com[m], "total": meses[m]} for m in sorted(meses)],
        "recentes": tabela,
        "trecho": trecho,
    }


# Transparência ativa

ROTULOS_CAMPOS = {
    "valorEstimado": "Valor estimado",
    "valorHomologado": "Valor homologado",
    "nomeContratada": "Nome da contratada",
    "tipoLicitacao": "Tipo de licitação",
    "situacao": "Situação",
    "numeroContrato": "Número do contrato",
    "numeroProcesso": "Número do processo",
    "dataFimVigencia": "Fim da vigência",
    "valorContrato": "Valor do contrato",
    "valor": "Valor",
    "dataExecucaoInicio": "Início da execução",
    "dataExecucaoFim": "Fim da execução",
}

CAMPOS_AUDITADOS = {
    "Licitações": ("licitacoes", ("valorEstimado", "valorHomologado", "situacao")),
    "Compras diretas": ("compra-direta", ("valorEstimado", "valorHomologado", "situacao")),
    "Contratos e atas": ("contratos", ("nomeContratada", "tipoLicitacao", "situacao",
                                       "numeroContrato", "valorContrato", "dataFimVigencia")),
    "Obras": ("obras", ("valor", "dataExecucaoInicio", "dataExecucaoFim")),
}


def campos_vazios(conjuntos: Dict[str, List[Dict]]) -> List[Dict]:
    """Parcela de registros sem cada campo essencial, do maior para o menor."""
    campos = []
    for rotulo, (nome, lista_campos) in CAMPOS_AUDITADOS.items():
        registros = conjuntos.get(nome) or []
        if not registros:
            continue
        for campo in lista_campos:
            vazios = sum(1 for r in registros if _vazio(r.get(campo)))
            if vazios:
                campos.append({
                    "conjunto": rotulo,
                    "campo": ROTULOS_CAMPOS.get(campo, campo),
                    "vazios": vazios,
                    "total": len(registros),
                    "pct": round(100 * vazios / len(registros)),
                })
    return sorted(campos, key=lambda c: (-c["pct"], -c["vazios"]))


def secoes_sem_dado(
    conjuntos_vazios: List[str],
    agregados: Dict[str, Dict],
    visoes_vazias: List[str],
    ano: int,
) -> List[Dict]:
    """Seções do portal e conjuntos de dados abertos que não entregam informação no ano."""
    nomes = {
        "contas-publicas": "Contas públicas",
        "relatorio-viagens": "Relatório de viagens",
        "concursos": "Editais de concurso",
        "audiencias-publicas": "Audiências públicas",
        "carta-servicos": "Carta de serviços",
        "chamamento-publico": "Chamamento público",
    }
    secoes = [
        {"nome": f"Despesas · {v}", "fato": f"A visão do portal não tem nenhum registro em {ano}."}
        for v in visoes_vazias
    ]
    zerados = [n for n, dados in agregados.items()
               if isinstance(dados, dict) and not dados.get("totalPedidos")]
    if zerados:
        secoes.append({
            "nome": " e ".join(n.upper() if n == "sic" else n.capitalize() for n in zerados),
            "fato": "Os conjuntos de dados abertos vêm zerados; o atendimento corre em outro sistema.",
        })
    secoes += [
        {"nome": nomes.get(c, c), "fato": f"O conjunto de {ano} responde “Nenhum registro encontrado”."}
        for c in conjuntos_vazios
    ]
    return secoes
