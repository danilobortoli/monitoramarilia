"""Testes do boletim semanal (dados e HTML, sem gerar PDF)."""

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from reports import boletim  # noqa: E402

VAZIO = {"novos": [], "alterados": [], "removidos": []}


def _historico(tmp_path):
    (tmp_path / "mudancas").mkdir()
    dentro = {
        "compra-direta": {**VAZIO, "novos": [{"modalidade": "Dispensa", "numeroProcesso": 555,
                                              "titulo": "Apresentação de DJ", "dataPostagem": "2026-10-09 08:00:00",
                                              "situacao": "Aberto"}]},
        "contratos": {**VAZIO, "novos": [{"tipo": "ARP", "numeroContrato": 200, "numeroProcesso": "91",
                                          "nomeContratada": None, "valorContrato": 6024,
                                          "dataAssinatura": "2026-10-07"}]},
        "licitacoes": VAZIO, "obras": VAZIO,
        "diario_oficial": {"novas": ["4298"], "alteradas": []},
        "despesas": {"novos": [1, 2, 3], "removidos": []},
    }
    fora = {**dentro, "compra-direta": {**VAZIO, "novos": [{"modalidade": "Dispensa", "numeroProcesso": 1}]}}
    (tmp_path / "mudancas" / "2026-10-09.json").write_text(json.dumps(dentro), encoding="utf-8")
    (tmp_path / "mudancas" / "2026-09-30.json").write_text(json.dumps(fora), encoding="utf-8")
    linhas = [{"data": "2026-10-02", "radar": {"contrato_sem_contratada": 470}},
              {"data": "2026-10-09", "radar": {"contrato_sem_contratada": 473}}]
    (tmp_path / "radar.jsonl").write_text("\n".join(json.dumps(l) for l in linhas) + "\n", encoding="utf-8")
    return tmp_path


OBSERVATORIO = {
    "exercicio": 2026,
    "totais": {"contratos": 1151, "contratos_vigentes": 1040},
    "regras": [{"id": "contrato_sem_contratada", "n": 2, "regra": "Contrato ou ata sem nome da contratada",
                "familia": "Contratos", "resultado": 473, "unidade": "sem nome", "fato": "473 dos 1.151."}],
    "diario": {"frase": "x", "com_frase": 105, "edicoes": 196,
               "recentes": [{"edicao": "4298", "data": "2026-10-09", "caracteres": 19444, "cnpjs": 3,
                             "dispensa": 4, "portarias": 4, "frase": True, "extra": False},
                            {"edicao": "4290", "data": "2026-09-29", "caracteres": 1, "cnpjs": 0,
                             "dispensa": 0, "portarias": 0, "frase": False, "extra": False}]},
    "notion": {"edicoes": [{"numero": 4298, "data": "2026-10-09", "situacao": "Analisada", "atos": 26,
                            "irregularidades": 2}],
               "achados": {"semana": {"novos": 3, "por_gravidade": {"grave": 1, "atencao": 2},
                                      "por_acao": {"LAI": 3}}}},
}


def test_montar_considera_so_as_sete_coletas_da_semana(tmp_path):
    b = boletim.montar(_historico(tmp_path), OBSERVATORIO, date(2026, 10, 9))
    assert b["inicio"] == "2026-10-03" and b["coletas"] == ["2026-10-09"]
    assert [c["numeroProcesso"] for c in b["novos"]["compra-direta"]] == [555]
    assert len(b["contratos_sem_nome"]) == 1
    assert b["edicoes_novas"] == ["4298"] and b["empenhos_novos"] == 3
    assert b["radar_desde"] == "2026-10-02"
    assert b["regras"][0]["inicio"] == 470 and b["regras"][0]["variacao"] == 3
    assert [e["edicao"] for e in b["diario"]["edicoes"]] == ["4298"]
    assert boletim.resumo(b) == ("Entraram 1 compra direta; 1 contrato ou ata (1 sem o nome da contratada); "
                                 "1 edição do Diário Oficial e 3 lançamentos de empenho.")


def test_html_traz_secoes_e_rotulos_legiveis(tmp_path):
    b = boletim.montar(_historico(tmp_path), OBSERVATORIO, date(2026, 10, 9))
    h = boletim.gerar_html(b)
    assert "3 a 9 de outubro de 2026" in h
    assert "Dispensa nº 555" in h and "+3" in h
    assert "1 graves" not in h and "2 pontos de atenção" in h and "pedidos de LAI" in h


def test_semana_sem_coleta(tmp_path):
    (tmp_path / "mudancas").mkdir()
    b = boletim.montar(tmp_path, {"regras": [], "exercicio": 2026}, date(2026, 10, 9))
    assert boletim.resumo(b) == "Não houve coleta com histórico nesta semana."
    assert "Boletim semanal" in boletim.gerar_html(b)
