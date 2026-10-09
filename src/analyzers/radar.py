"""
Regras do Radar de alertas do Observatório MATRA.

Cada regra recebe registros já coletados (portal e dados abertos da
Prefeitura de Marília) e devolve um resultado no mesmo formato:

    {"id", "familia", "regra", "fonte", "base", "resultado", "itens"}

Os itens são registros que pedem leitura, não constatação de irregularidade.
"""

import re
import statistics
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional

from collectors.portal_marilia import parse_valor

MAX_ITENS = 20


def _vazio(valor) -> bool:
    return valor is None or str(valor).strip() == ""


def _data(valor: Optional[str]) -> Optional[date]:
    """Lê '2026-10-09', '2026-10-09 08:00:00' ou '09/10/2026 00:00'."""
    if _vazio(valor):
        return None
    texto = str(valor).strip()
    for formato, tamanho in (("%Y-%m-%d", 10), ("%d/%m/%Y", 10)):
        try:
            return datetime.strptime(texto[:tamanho], formato).date()
        except ValueError:
            continue
    return None


def _data_br(valor: Optional[str]) -> str:
    """'2026-10-07' -> '07.10.2026'."""
    d = _data(valor)
    return d.strftime("%d.%m.%Y") if d else ""


def _digitos(valor) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def mascarar_documento(valor) -> str:
    """Mantém o CNPJ e mascara o CPF de pessoa física (***.456.789-**)."""
    numeros = _digitos(valor)
    if len(numeros) == 14:
        return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"
    if len(numeros) == 11:
        return f"***.{numeros[3:6]}.{numeros[6:9]}-**"
    return ""


def numero(valor: float) -> str:
    """12345 -> '12.345'."""
    return f"{valor:,.0f}".replace(",", ".")


def moeda(valor: float) -> str:
    """1234.5 -> 'R$ 1.234,50'."""
    texto = f"{valor:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return f"R$ {texto}"


def _normalizar_nome(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento).strip().upper()


def chave_fornecedor(documento, nome: str = "") -> str:
    """
    Identifica o fornecedor sem guardar CPF por extenso.

    CNPJ fica como está (é público). Para CPF, usa os seis dígitos que a máscara
    deixa à vista e o nome normalizado: o mesmo que o Observatório já exibe.
    """
    numeros = _digitos(documento)
    if len(numeros) == 11:
        return f"cpf:{numeros[3:9]}:{_normalizar_nome(nome)}"
    return numeros


def _resultado(id_, familia, regra, fonte, base, itens, unidade="", fato="", ordenar=None) -> Dict:
    if ordenar:
        itens = sorted(itens, key=ordenar, reverse=True)
    return {
        "id": id_,
        "familia": familia,
        "regra": regra,
        "fonte": fonte,
        "base": base,
        "resultado": len(itens),
        "unidade": unidade,
        "fato": fato,
        "itens": itens[:MAX_ITENS],
    }


def compra_direta_aberta(compras: List[Dict]) -> Dict:
    """1. Dispensas e inexigibilidades ainda abertas."""
    itens = [
        {
            "processo": c.get("numeroProcesso"),
            "modalidade": c.get("modalidade"),
            "titulo": (c.get("titulo") or "").strip(),
            "data": (c.get("dataPostagem") or "")[:10],
            "sem_valor_estimado": _vazio(c.get("valorEstimado")),
        }
        for c in compras
        if c.get("situacao") == "Aberto"
    ]
    modalidades = Counter(c.get("modalidade") for c in compras)
    sem_valor = sum(1 for c in compras if _vazio(c.get("valorEstimado")))
    fato = (
        f"São {numero(modalidades.get('Dispensa', 0))} dispensas e "
        f"{numero(modalidades.get('Inexigibilidade', 0))} inexigibilidades no ano. "
        f"{numero(sem_valor)} dos {numero(len(compras))} registros não trazem valor estimado."
    )
    return _resultado(
        "compra_direta_aberta", "Contratação direta", "Nova dispensa ou inexigibilidade",
        "Dados abertos · compra direta", len(compras), itens, unidade="abertas", fato=fato,
        ordenar=lambda i: i["data"],
    )


def contrato_sem_contratada(contratos: List[Dict]) -> Dict:
    """2. Contrato ou ata publicado sem o nome da contratada."""
    itens = [
        {
            "numero": c.get("numeroContrato"),
            "processo": c.get("numeroProcesso"),
            "tipo": c.get("tipo"),
            "valor": c.get("valorContrato"),
            "assinatura": c.get("dataAssinatura"),
        }
        for c in contratos
        if _vazio(c.get("nomeContratada"))
    ]
    fato = ""
    if itens:
        recentes = sorted(itens, key=lambda i: i["assinatura"] or "", reverse=True)
        ultima = recentes[0]["assinatura"]
        do_dia = [i for i in recentes if i["assinatura"] == ultima]
        soma = sum(float(i["valor"] or 0) for i in do_dia)
        fato = (
            f"{numero(len(itens))} dos {numero(len(contratos))} registros do ano não identificam o "
            f"fornecedor. Os mais recentes, assinados em {_data_br(ultima)}, são {len(do_dia)} e "
            f"somam {moeda(soma)}."
        )
    return _resultado(
        "contrato_sem_contratada", "Contratos", "Contrato ou ata sem nome da contratada",
        "Dados abertos · contratos", len(contratos), itens, unidade="sem nome", fato=fato,
        ordenar=lambda i: i["assinatura"] or "",
    )


def licitacao_sem_valor(licitacoes: List[Dict]) -> Dict:
    """3. Licitação publicada sem valor estimado."""
    itens = [
        {
            "processo": l.get("numeroProcesso"),
            "modalidade": l.get("modalidade"),
            "situacao": l.get("situacao"),
            "titulo": (l.get("titulo") or "").strip(),
            "data": (l.get("dataRealizacao") or "")[:10],
        }
        for l in licitacoes
        if _vazio(l.get("valorEstimado"))
    ]
    abertas = sum(1 for l in licitacoes if l.get("situacao") == "Aberto")
    fato = (
        f"{numero(len(itens))} das {numero(len(licitacoes))} licitações do ano não trazem valor "
        f"estimado no conjunto de dados; {numero(abertas)} estão abertas."
    )
    return _resultado(
        "licitacao_sem_valor", "Licitações", "Licitação sem valor estimado",
        "Dados abertos · licitações", len(licitacoes), itens, unidade="sem valor", fato=fato,
        ordenar=lambda i: i["data"],
    )


# Justificativa publicada no Diário: "...com fundamento no artigo 141, §1º, inciso III
# e V da Lei Federal nº 14.133/2021, torna pública a presente justificativa para a
# quebra da ordem cronológica de pagamentos..."
_QUEBRA_ORDEM = re.compile(r"141,\s*§\s*1", re.IGNORECASE)


def quebra_ordem_cronologica(edicoes: List[Dict]) -> Dict:
    """4. Edições do Diário Oficial com justificativa de quebra da ordem cronológica."""
    itens = [
        {"edicao": e.get("edicao"), "data": (e.get("data") or "")[:10]}
        for e in edicoes
        if _QUEBRA_ORDEM.search(e.get("descricao") or "")
    ]
    fato = ""
    if itens:
        primeira = min(itens, key=lambda i: i["data"])
        fato = (
            f"A justificativa com base no art. 141, §1º, consta de {numero(len(itens))} das "
            f"{numero(len(edicoes))} edições do ano, desde a nº {primeira['edicao']}."
        )
    return _resultado(
        "quebra_ordem_cronologica", "Pagamentos", "Quebra da ordem cronológica",
        "Diário Oficial", len(edicoes), itens, unidade="com a justificativa", fato=fato,
        ordenar=lambda i: i["data"],
    )


def _empenhos_por_fornecedor(despesas: Iterable[Dict]) -> Dict[str, Dict]:
    """Soma o empenhado por fornecedor em 'Despesas e Investimentos' (uma linha por empenho)."""
    fornecedores: Dict[str, Dict] = {}
    for d in despesas:
        nome = (d.get("NomeFornecedor") or "").strip()
        chave = chave_fornecedor(d.get("CNPJ"), nome)
        if not chave:
            continue
        f = fornecedores.setdefault(chave, {
            "nome": nome,
            "documento": mascarar_documento(d.get("CNPJ")),
            "empenhado": 0.0,
            "lancamentos": 0,
        })
        f["empenhado"] += parse_valor(d.get("ValorEmpenhado"))
        f["lancamentos"] += 1
    return fornecedores


def fornecedores_conhecidos(despesas: Iterable[Dict]) -> List[str]:
    """Chaves dos fornecedores com algum lançamento, para o cache de anos anteriores."""
    return sorted(_empenhos_por_fornecedor(despesas))


def fornecedor_novo_valor_alto(
    despesas_ano: List[Dict],
    conhecidos: Iterable[str],
    limite: float = 100_000.0,
    anos_anteriores: str = "",
) -> Dict:
    """
    5. Fornecedor sem empenho nos exercícios anteriores e com empenhado alto no ano.

    Args:
        conhecidos: Chaves (chave_fornecedor) de quem recebeu empenho nos anos anteriores
        limite: Empenhado mínimo no ano para entrar no radar
        anos_anteriores: Rótulo dos exercícios comparados (vai para a base)
    """
    atuais = _empenhos_por_fornecedor(despesas_ano)
    conhecidos = set(conhecidos)
    itens = [
        {
            "fornecedor": f["nome"],
            "documento": f["documento"],
            "empenhado": round(f["empenhado"], 2),
            "lancamentos": f["lancamentos"],
        }
        for chave, f in atuais.items()
        if chave not in conhecidos and f["empenhado"] >= limite
    ]
    base = f"{numero(len(atuais))} fornecedores no ano"
    if anos_anteriores:
        base += f", comparados com {anos_anteriores}"
    fato = ""
    if itens:
        maior = max(itens, key=lambda i: i["empenhado"])
        soma = sum(i["empenhado"] for i in itens)
        fato = (
            f"{numero(len(itens))} fornecedores sem empenho em {anos_anteriores or 'anos anteriores'} "
            f"receberam ao menos {moeda(limite)} em empenhos no ano, somando {moeda(soma)}. "
            f"O maior é {maior['fornecedor']}, com {moeda(maior['empenhado'])}."
        )
    return _resultado(
        "fornecedor_novo_valor_alto", "Fornecedores", "Fornecedor novo com valor alto",
        "Portal · despesas e investimentos", base, itens, unidade="novos", fato=fato,
        ordenar=lambda i: i["empenhado"],
    )


def diarias_atipicas(diarias: List[Dict], fator_iqr: float = 3.0, minimo_por_cargo: int = 5) -> Dict:
    """
    6. Beneficiários cujo total de diárias no ano fica muito acima do de colegas do mesmo cargo.

    Critério: total acima de Q3 + fator_iqr × (Q3 − Q1) da distribuição dos totais
    por beneficiário dentro do cargo. Cargos com menos de `minimo_por_cargo`
    beneficiários não são avaliados (não há com quem comparar).
    """
    por_beneficiario: Dict[tuple, Dict] = defaultdict(lambda: {"total": 0.0, "registros": 0})
    for d in diarias:
        nome = (d.get("NomeFornecedor") or "").strip()
        if not nome:
            continue
        cargo = (d.get("Cargo") or "").strip() or "Cargo não informado"
        b = por_beneficiario[(cargo, nome)]
        b["total"] += parse_valor(d.get("ValorEmpenhado"))
        b["registros"] += 1
        b.setdefault("secretaria", (d.get("Secretaria") or "").strip())

    por_cargo: Dict[str, List[float]] = defaultdict(list)
    for (cargo, _), b in por_beneficiario.items():
        por_cargo[cargo].append(b["total"])

    cortes = {}
    for cargo, totais_cargo in por_cargo.items():
        if len(totais_cargo) >= minimo_por_cargo:
            q1, _, q3 = statistics.quantiles(totais_cargo, n=4)
            cortes[cargo] = q3 + fator_iqr * (q3 - q1)

    itens = [
        {
            "beneficiario": nome,
            "cargo": cargo,
            "secretaria": b["secretaria"],
            "total": round(b["total"], 2),
            "registros": b["registros"],
            "corte_do_cargo": round(cortes[cargo], 2),
        }
        for (cargo, nome), b in por_beneficiario.items()
        if cargo in cortes and b["total"] > cortes[cargo]
    ]
    fato = (
        f"Cada beneficiário é comparado com colegas do mesmo cargo; {numero(len(cortes))} cargos "
        f"têm ao menos {minimo_por_cargo} beneficiários."
    )
    if itens:
        maior = max(itens, key=lambda i: i["total"])
        fato += (
            f" O maior desvio é de {maior['cargo'].lower()}, com {moeda(maior['total'])} no ano, "
            f"para um corte de {moeda(maior['corte_do_cargo'])} no cargo."
        )
    return _resultado(
        "diarias_atipicas", "Pessoal", "Diárias atípicas", "Portal · diárias",
        f"{numero(len(diarias))} registros, {numero(len(cortes))} cargos comparáveis", itens,
        unidade="acima do cargo", fato=fato, ordenar=lambda i: i["total"],
    )


def obra_parada_ou_cancelada(obras: List[Dict]) -> Dict:
    """7. Obras com situação cancelada ou paralisada."""
    itens = [
        {
            "obra": (o.get("titulo") or "").strip(),
            "categoria": o.get("categoria"),
            "situacao": o.get("situacao"),
            "valor": o.get("valor"),
            "inicio": o.get("dataExecucaoInicio"),
        }
        for o in obras
        if re.search(r"cancel|paralis|parad", o.get("situacao") or "", re.IGNORECASE)
    ]
    situacoes = Counter(o.get("situacao") for o in obras)
    plurais = {"Concluído": "concluídas", "Cancelada": "canceladas", "Paralisada": "paralisadas"}
    partes = ", ".join(f"{numero(n)} {plurais.get(s, s.lower())}" for s, n in situacoes.most_common() if s)
    fato = f"Das {numero(len(obras))} obras, {partes}."
    if itens:
        maior = max(itens, key=lambda i: i["valor"] or 0)
        fato += f" A de maior valor entre as paradas ou canceladas é {maior['obra']}, de {moeda(maior['valor'] or 0)}."
    return _resultado(
        "obra_parada_ou_cancelada", "Obras", "Obra parada ou cancelada",
        "Dados abertos · obras", len(obras), itens, unidade="paradas ou canceladas", fato=fato,
        ordenar=lambda i: i["valor"] or 0,
    )


def contrato_a_vencer(contratos: List[Dict], hoje: Optional[date] = None, dias: int = 60) -> Dict:
    """8. Contratos vigentes que terminam nos próximos `dias` dias."""
    hoje = hoje or date.today()
    limite = hoje + timedelta(days=dias)
    vigentes = [c for c in contratos if c.get("situacao") == "Vigente"]
    itens = []
    for c in vigentes:
        fim = _data(c.get("dataFimVigencia"))
        if fim and hoje <= fim <= limite:
            itens.append({
                "numero": c.get("numeroContrato"),
                "contratada": c.get("nomeContratada"),
                "tipo": c.get("tipo"),
                "valor": c.get("valorContrato"),
                "fim": fim.isoformat(),
            })
    itens.sort(key=lambda i: i["fim"])
    fato = ""
    if itens:
        soma = sum(float(i["valor"] or 0) for i in itens)
        sem_nome = sum(1 for i in itens if _vazio(i["contratada"]))
        fato = (
            f"{numero(len(itens))} contratos e atas vigentes terminam até {_data_br(limite.isoformat())}, "
            f"somando {moeda(soma)}; {numero(sem_nome)} deles não identificam a contratada."
        )
    return _resultado(
        "contrato_a_vencer", "Contratos", f"Contrato a vencer em {dias} dias",
        "Dados abertos · contratos", f"{numero(len(vigentes))} vigentes", itens,
        unidade="a vencer", fato=fato,
    )


def totais(compras, licitacoes, contratos, obras, despesas_ano) -> Dict:
    """Números de cabeçalho do painel."""
    contagem = lambda lista, campo, valor: sum(1 for r in lista if r.get(campo) == valor)
    return {
        "compras_diretas": len(compras),
        "dispensas": contagem(compras, "modalidade", "Dispensa"),
        "inexigibilidades": contagem(compras, "modalidade", "Inexigibilidade"),
        "licitacoes": len(licitacoes),
        "licitacoes_abertas": contagem(licitacoes, "situacao", "Aberto"),
        "contratos": len(contratos),
        "contratos_vigentes": contagem(contratos, "situacao", "Vigente"),
        "obras": len(obras),
        "obras_em_andamento": contagem(obras, "situacao", "Em Andamento"),
        "obras_concluidas": contagem(obras, "situacao", "Concluído"),
        "obras_canceladas": contagem(obras, "situacao", "Cancelada"),
        # 'Despesas e Investimentos' traz empenhos e anulações (com valor negativo),
        # da Prefeitura e da Câmara.
        "empenhos": contagem(despesas_ano, "TipEmpenho", "Empenho"),
        "anulacoes": contagem(despesas_ano, "TipEmpenho", "Anulação de Empenho"),
        "empenhado_liquido": round(sum(parse_valor(d.get("ValorEmpenhado")) for d in despesas_ano), 2),
    }
