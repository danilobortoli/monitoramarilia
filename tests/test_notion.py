"""Testes da leitura do Notion com respostas no formato da API (sem rede)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from collectors.notion_matra import NotionMatraCollector, resumir_achados  # noqa: E402


class Resposta:
    def __init__(self, dados):
        self.dados = dados

    def raise_for_status(self):
        pass

    def json(self):
        return self.dados


class SessaoFalsa:
    """Responde às consultas por base; registra o corpo de cada consulta."""

    def __init__(self, paginas_por_base, propriedades_casos):
        self.headers = {}
        self.paginas = paginas_por_base
        self.propriedades_casos = propriedades_casos
        self.consultas = []

    def post(self, url, json=None, timeout=None):
        base = url.split("/databases/")[1].split("/")[0]
        self.consultas.append((base, json))
        paginas = self.paginas[base]
        # Duas páginas de resultado para exercitar a paginação.
        if json.get("start_cursor") == "c2":
            return Resposta({"results": paginas[1:], "has_more": False})
        return Resposta({"results": paginas[:1], "has_more": len(paginas) > 1, "next_cursor": "c2"})

    def get(self, url, timeout=None):
        return Resposta({"properties": self.propriedades_casos})


def _titulo(texto):
    return {"type": "title", "title": [{"plain_text": texto}]}


def _texto(texto):
    return {"type": "rich_text", "rich_text": [{"plain_text": texto}]}


def _num(n):
    return {"type": "number", "number": n}


def _sel(nome):
    return {"type": "select", "select": {"name": nome} if nome else None}


def _data(d):
    return {"type": "date", "date": {"start": d}}


EDICOES = [
    {"properties": {"Edição": _titulo("DOMM 4298"), "Número": _num(4298), "Data": _data("2026-10-09"),
                    "Situação": _sel("Analisada"), "Origem": _sel("Nuvem"), "Atos": _num(26),
                    "Páginas": _num(11), "Irregularidades": _num(2)}},
    {"properties": {"Edição": _titulo("DOMM 4297"), "Número": _num(4297), "Data": _data("2026-10-08"),
                    "Situação": _sel("Analisada"), "Origem": _sel("Nuvem"), "Atos": _num(40),
                    "Páginas": _num(16), "Irregularidades": _num(1)}},
]

ACHADOS = [
    {"properties": {"ID": _titulo("IRR-4298-001"), "Edição": _num(4298), "Data DOMM": _data("2026-10-09"),
                    "Tipo": _sel("Irregularidade"), "Gravidade": _sel("grave"), "Status": _sel("aberta"),
                    "Ação": _sel("LAI")}},
    {"properties": {"ID": _titulo("ATN-4297-001"), "Edição": _num(4297), "Data DOMM": _data("2026-10-08"),
                    "Tipo": _sel("Ponto de atenção"), "Gravidade": _sel("media"), "Status": _sel("oficiada"),
                    "Ação": _sel("oficio")}},
    {"properties": {"ID": _titulo("IRR-4280-002"), "Edição": _num(4280), "Data DOMM": _data("2026-09-15"),
                    "Tipo": _sel("Irregularidade"), "Gravidade": _sel("grave"), "Status": _sel("sanada"),
                    "Ação": _sel("LAI")}},
]

CASOS = [
    {"properties": {"Caso": _titulo("Parque da Criança, CP 012/2026"), "Fase": _texto("Representação ao TCE-SP")}},
]

BASES = {"edicoes": "E", "achados": "A", "casos": "C"}


def test_resumo_le_edicoes_achados_e_casos_publicos():
    sessao = SessaoFalsa({"E": EDICOES, "A": ACHADOS, "C": CASOS},
                         {"Caso": {}, "No Observatório": {"type": "checkbox"}})
    leitor = NotionMatraCollector(BASES, token="x", session=sessao)
    r = leitor.resumo(inicio_semana="2026-10-03")

    assert [e["numero"] for e in r["edicoes"]] == [4298, 4297]
    assert r["edicoes"][0] == {"numero": 4298, "data": "2026-10-09", "situacao": "Analisada",
                               "origem": "Nuvem", "atos": 26, "paginas": 11, "irregularidades": 2}
    a = r["achados"]
    assert a["total"] == 3 and a["em_aberto"] == 2
    assert a["em_aberto_por_tipo"] == {"Irregularidade": 1, "Ponto de atenção": 1}
    assert a["ultimas_edicoes"] == [4298, 4297]
    assert a["em_aberto_ultimas_edicoes"] == 2 and a["graves_ultimas_edicoes"] == 1
    assert a["semana"]["novos"] == 2
    assert r["casos"] == [{"caso": "Parque da Criança, CP 012/2026", "fase": "Representação ao TCE-SP"}]

    # A consulta de casos filtra frente, status e a caixa de publicação.
    corpo_casos = [c for base, c in sessao.consultas if base == "C"][0]
    filtros = {f["property"] for f in corpo_casos["filter"]["and"]}
    assert filtros == {"Frente", "Status", "No Observatório"}


def test_sem_caixa_de_publicacao_nenhum_caso_sai_do_notion():
    sessao = SessaoFalsa({"E": EDICOES, "A": ACHADOS, "C": CASOS}, {"Caso": {}})
    leitor = NotionMatraCollector(BASES, token="x", session=sessao)
    assert leitor.casos_publicos() is None
    assert not [base for base, _ in sessao.consultas if base == "C"]


def test_sem_token_fica_inativo():
    assert not NotionMatraCollector(BASES, token="").ativo


def test_resumir_achados_sem_semana():
    r = resumir_achados([], [4298], None)
    assert r["em_aberto"] == 0 and r["semana"]["novos"] == 0
