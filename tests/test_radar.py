"""Testes das regras do Radar e dos auxiliares dos coletores de Marília (sem rede)."""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from analyzers import radar  # noqa: E402
from collectors.portal_marilia import parse_valor  # noqa: E402


def test_parse_valor_formato_do_portal():
    assert parse_valor("1.000.000,00") == 1_000_000.0
    assert parse_valor("-25.176,47") == -25_176.47
    assert parse_valor("432,84") == 432.84
    assert parse_valor("") == 0.0
    assert parse_valor(None) == 0.0
    assert parse_valor(6024) == 6024.0


def test_mascarar_documento_preserva_cnpj_e_mascara_cpf():
    assert radar.mascarar_documento("68395240000176") == "68.395.240/0001-76"
    assert radar.mascarar_documento("004.716.258-92      ") == "***.716.258-**"
    assert radar.mascarar_documento("") == ""


def test_compra_direta_aberta():
    compras = [
        {"situacao": "Aberto", "modalidade": "Dispensa", "numeroProcesso": 555,
         "titulo": " DJ ", "dataPostagem": "2026-10-09 08:00:00", "valorEstimado": ""},
        {"situacao": "Homologado", "modalidade": "Dispensa", "dataPostagem": "2026-10-01 08:00:00"},
    ]
    r = radar.compra_direta_aberta(compras)
    assert r["resultado"] == 1
    assert r["base"] == 2
    assert r["itens"][0] == {"processo": 555, "modalidade": "Dispensa", "titulo": "DJ",
                             "data": "2026-10-09", "sem_valor_estimado": True}


def test_contrato_sem_contratada_e_licitacao_sem_valor():
    contratos = [{"nomeContratada": None}, {"nomeContratada": "  "}, {"nomeContratada": "ACME"}]
    assert radar.contrato_sem_contratada(contratos)["resultado"] == 2
    licitacoes = [{"valorEstimado": ""}, {"valorEstimado": "1000,00"}]
    assert radar.licitacao_sem_valor(licitacoes)["resultado"] == 1


def test_quebra_ordem_cronologica_reconhece_a_justificativa_do_diario():
    texto = ("ORDEM CRONOLÓGICA\nA Prefeitura Municipal de Marília, com fundamento no artigo 141, "
             "§1º, inciso III e V da Lei Federal nº 14.133/2021, torna pública a presente justificativa")
    edicoes = [
        {"edicao": "4298", "data": "2026-10-09 00:01:00", "descricao": texto},
        {"edicao": "4297", "data": "2026-10-08 00:01:00", "descricao": "PORTARIA NÚMERO 49761"},
    ]
    r = radar.quebra_ordem_cronologica(edicoes)
    assert r["resultado"] == 1
    assert r["itens"] == [{"edicao": "4298", "data": "2026-10-09"}]


def test_fornecedor_novo_valor_alto_ignora_conhecidos_e_desconta_anulacoes():
    ano = [
        {"CNPJ": "11.111.111/0001-11", "NomeFornecedor": "NOVA", "ValorEmpenhado": "150.000,00"},
        {"CNPJ": "11.111.111/0001-11", "NomeFornecedor": "NOVA", "ValorEmpenhado": "-10.000,00"},
        {"CNPJ": "22.222.222/0001-22", "NomeFornecedor": "ANTIGA", "ValorEmpenhado": "500.000,00"},
        {"CNPJ": "33.333.333/0001-33", "NomeFornecedor": "PEQUENA", "ValorEmpenhado": "5.000,00"},
    ]
    anteriores = [{"CNPJ": "22222222000122", "NomeFornecedor": "ANTIGA", "ValorEmpenhado": "1,00"}]
    r = radar.fornecedor_novo_valor_alto(ano, anteriores, limite=100_000)
    assert r["resultado"] == 1
    assert r["itens"][0]["fornecedor"] == "NOVA"
    assert r["itens"][0]["empenhado"] == 140_000.0
    assert r["itens"][0]["lancamentos"] == 2


def test_diarias_atipicas_compara_dentro_do_cargo():
    diarias = []
    # Nove motoristas com totais parecidos e um muito acima.
    totais = ["1.000,00", "1.100,00", "900,00", "1.050,00", "950,00",
              "1.020,00", "980,00", "1.010,00", "990,00", "9.000,00"]
    for i, total in enumerate(totais):
        diarias.append({"NomeFornecedor": f"Motorista {i}", "Cargo": "Motorista",
                        "ValorEmpenhado": total})
    # Secretário com total alto, mas sem colegas suficientes para comparar.
    diarias.append({"NomeFornecedor": "Secretário", "Cargo": "Secretário", "ValorEmpenhado": "20.000,00"})
    r = radar.diarias_atipicas(diarias)
    assert [i["beneficiario"] for i in r["itens"]] == ["Motorista 9"]


def test_obra_parada_ou_cancelada():
    obras = [{"situacao": "Cancelada", "valor": 10}, {"situacao": "Paralisada", "valor": 5},
             {"situacao": "Em Andamento", "valor": 1}]
    assert radar.obra_parada_ou_cancelada(obras)["resultado"] == 2


def test_contrato_a_vencer_considera_so_vigentes_na_janela():
    hoje = date(2026, 10, 9)
    contratos = [
        {"situacao": "Vigente", "dataFimVigencia": "2026-10-20", "numeroContrato": 1},
        {"situacao": "Vigente", "dataFimVigencia": "2027-10-08", "numeroContrato": 2},
        {"situacao": "Vigente", "dataFimVigencia": "2026-10-01", "numeroContrato": 3},
        {"situacao": "Rescindido", "dataFimVigencia": "2026-10-15", "numeroContrato": 4},
    ]
    r = radar.contrato_a_vencer(contratos, hoje=hoje, dias=60)
    assert [i["numero"] for i in r["itens"]] == [1]
    assert r["base"] == "3 vigentes"


def test_totais_separa_empenhos_de_anulacoes():
    despesas = [
        {"TipEmpenho": "Empenho", "ValorEmpenhado": "100,00"},
        {"TipEmpenho": "Anulação de Empenho", "ValorEmpenhado": "-30,00"},
    ]
    t = radar.totais([], [], [], [], despesas)
    assert t["empenhos"] == 1
    assert t["anulacoes"] == 1
    assert t["empenhado_liquido"] == 70.0
