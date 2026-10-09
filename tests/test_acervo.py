"""Testes do histórico entre coletas e dos dados das páginas (sem rede)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from analyzers import paineis  # noqa: E402
from analyzers.acervo import Acervo, comparar  # noqa: E402


def _contrato(numero, processo="91", nome=None, valor=100, atualizado="2026-10-08 10:00:00"):
    return {"tipo": "ARP - Ata de Registro de Preço", "numeroContrato": numero,
            "numeroProcesso": processo, "nomeContratada": nome, "valorContrato": valor,
            "dataAtualizacao": atualizado}


def test_comparar_separa_novos_alterados_e_removidos():
    anteriores = [_contrato(1), _contrato(2), _contrato(3)]
    atuais = [
        _contrato(1, atualizado="2026-10-09 09:00:00"),  # só a data de atualização mudou
        _contrato(2, nome="ACME LTDA"),                   # ganhou a contratada
        _contrato(4),                                     # novo
    ]
    m = comparar("contratos", anteriores, atuais)
    assert [r["numeroContrato"] for r in m["novos"]] == [4]
    assert [r["numeroContrato"] for r in m["removidos"]] == [3]
    assert len(m["alterados"]) == 1
    assert m["alterados"][0]["campos"] == {"nomeContratada": [None, "ACME LTDA"]}


def test_comparar_lida_com_registros_repetidos():
    # O conjunto de contratos tem registros repetidos por completo.
    anteriores = [_contrato(1)]
    atuais = [_contrato(1), _contrato(1)]
    m = comparar("contratos", anteriores, atuais)
    assert len(m["novos"]) == 1 and not m["removidos"] and not m["alterados"]


def test_acervo_estado_e_cache(tmp_path):
    acervo = Acervo(tmp_path)
    assert acervo.ler_estado("contratos", 2026) is None
    acervo.gravar_estado("contratos", 2026, [_contrato(1)])
    assert acervo.ler_estado("contratos", 2026) == [_contrato(1)]
    # Na virada do ano, o estado anterior não serve de comparação.
    assert acervo.ler_estado("contratos", 2027) is None

    acervo.gravar_fornecedores_conhecidos([2024, 2025], ["b", "a"])
    assert acervo.ler_fornecedores_conhecidos([2024, 2025]) == ["a", "b"]
    assert acervo.ler_fornecedores_conhecidos([2025, 2026]) is None

    acervo.registrar_coleta({"data": "2026-10-09", "radar": {"x": 1}})
    acervo.registrar_coleta({"data": "2026-10-09", "radar": {"x": 2}})
    acervo.registrar_coleta({"data": "2026-10-10", "radar": {"x": 3}})
    assert [l["radar"]["x"] for l in acervo.serie()] == [2, 3]


def test_serie_contratacao_direta():
    por_ano = {2026: [
        {"tipoLic": "DISPENSA      ", "ValorEmpenhado": "10,00"},
        {"tipoLic": "INEXIGIBILIDADE", "ValorEmpenhado": "10,00"},
        {"tipoLic": "Outros/Não Aplicavel", "ValorEmpenhado": "60,00"},
        {"tipoLic": "PREGÃO ELETRÔNICO", "ValorEmpenhado": "20,00"},
    ]}
    s = paineis.serie_contratacao_direta(por_ano)
    assert s == [{"ano": 2026, "direta": 20.0, "total": 100.0,
                  "pct_direta": 20.0, "pct_sem_modalidade": 60.0}]


FRASE = "A interrupção de serviços contratados pode gerar impactos diretos à população"


def test_diario_conta_frase_e_extrai_trecho():
    edicoes = [
        {"edicao": "4297", "data": "2026-10-08 00:01:00", "descricao": "PORTARIA NÚMERO 1\nDispensa"},
        {"edicao": "4298", "data": "2026-10-09 00:01:00", "edicaoExtra": "S",
         "descricao": f"Risco de Descontinuidade Operacional.\n{FRASE}. A ausência de pagamentos.\n"
                      "Fundamentação Legal.\nArt. 141. CNPJ 12.345.678/0001-90"},
    ]
    d = paineis.diario(edicoes, FRASE)
    assert d["edicoes"] == 2 and d["extras"] == 1 and d["com_frase"] == 1
    assert d["faixa"] == [0, 1]
    assert d["meses"] == [{"mes": "out", "com": 1, "total": 2}]
    assert d["recentes"][0]["edicao"] == "4298" and d["recentes"][0]["cnpjs"] == 1
    assert d["recentes"][1]["portarias"] == 1 and d["recentes"][1]["dispensa"] == 1
    assert d["trecho"]["antes"] == "Risco de Descontinuidade Operacional."
    assert d["trecho"]["frase"] == FRASE


def test_campos_vazios_ordena_pela_parcela():
    conjuntos = {"licitacoes": [{"valorEstimado": "", "valorHomologado": "", "situacao": "Aberto"}] * 2,
                 "contratos": [{"nomeContratada": None, "numeroContrato": 1, "tipoLicitacao": "x",
                                "situacao": "Vigente", "valorContrato": 1, "dataFimVigencia": "2027-01-01"},
                               {"nomeContratada": "ACME", "numeroContrato": 2, "tipoLicitacao": "x",
                                "situacao": "Vigente", "valorContrato": 1, "dataFimVigencia": "2027-01-01"}]}
    campos = paineis.campos_vazios(conjuntos)
    assert [(c["conjunto"], c["campo"], c["pct"]) for c in campos] == [
        ("Licitações", "Valor estimado", 100),
        ("Licitações", "Valor homologado", 100),
        ("Contratos e atas", "Nome da contratada", 50),
    ]


def test_novidades_com_mudancas():
    contrato = _contrato(200, nome=None, valor=1000)
    contrato["dataAssinatura"] = "2026-10-09"
    mudancas = {
        "compra-direta": {"novos": [], "alterados": [], "removidos": []},
        "contratos": {"novos": [contrato], "alterados": [], "removidos": []},
        "licitacoes": {"novos": [], "alterados": [], "removidos": []},
        "obras": {"novos": [], "alterados": [], "removidos": []},
        "diario_oficial": {"novas": [], "alteradas": []},
        "despesas": {"novos": [7], "removidos": []},
    }
    despesas = [
        {"ID": 7, "TipEmpenho": "Empenho", "CNPJ": "11.111.111/0001-11", "NomeFornecedor": "ACME",
         "NroEmpenho": 1, "ValorEmpenhado": "5.000,00", "DataMovEmp": "09/10/2026 00:00", "UG": "PREFEITURA"},
        {"ID": 8, "TipEmpenho": "Empenho", "CNPJ": "004.716.258-92", "NomeFornecedor": "PESSOA",
         "NroEmpenho": 2, "ValorEmpenhado": "9.000,00", "DataMovEmp": "09/10/2026 00:00", "UG": "PREFEITURA"},
    ]
    n = paineis.novidades(mudancas, [], [contrato], [], [], despesas, FRASE)
    assert not n["linha_de_base"]
    assert [i["titulo"] for i in n["itens"]] == [
        "1 contrato ou ata sem o nome da contratada",
        "Empenho nº 1 a ACME",
    ]
    assert n["resumo"] == ("entraram 1 contrato ou ata novo, 1 sem o nome da contratada "
                           "e 1 empenho novo.")
    vazio = {k: ({"novos": [], "alterados": [], "removidos": []} if "novos" in v and "alterados" in v else v)
             for k, v in mudancas.items()}
    vazio["despesas"] = {"novos": [], "removidos": []}
    assert paineis.novidades(vazio, [], [], [], [], [], FRASE)["resumo"] == (
        "nenhum registro novo nos conjuntos acompanhados.")
