"""
Coletor de dados de despesas do Portal de Transparência de Marília.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, date
from .base import BaseCollector
import logging

logger = logging.getLogger(__name__)


class DespesasCollector(BaseCollector):
    """
    Coletor de despesas públicas (empenho, liquidação, pagamento).
    """

    ENDPOINT = "/api/despesas"

    def get_source_name(self) -> str:
        return "Despesas - Portal de Transparência de Marília"

    def collect(
        self,
        ano: Optional[int] = None,
        mes: Optional[int] = None,
        orgao: Optional[str] = None,
        favorecido: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Coleta dados de despesas.

        Args:
            ano: Ano de referência
            mes: Mês de referência (1-12)
            orgao: Filtrar por órgão/secretaria
            favorecido: Filtrar por nome ou CNPJ do favorecido

        Returns:
            Lista de despesas
        """
        if ano is None:
            ano = datetime.now().year

        url = f"{self.BASE_URL}{self.ENDPOINT}"
        params = {"ano": ano}

        if mes:
            params["mes"] = mes
        if orgao:
            params["orgao"] = orgao
        if favorecido:
            params["favorecido"] = favorecido

        logger.info(f"Coletando despesas de {mes or 'todos os meses'}/{ano}...")

        response = self._make_request(url, params=params)

        if response is None:
            logger.warning("API não disponível")
            return []

        try:
            data = response.json()
            despesas = self._parse_response(data)
            logger.info(f"Coletadas {len(despesas)} despesas")
            return despesas
        except Exception as e:
            logger.error(f"Erro ao processar resposta: {e}")
            return []

    def _parse_response(self, data: Any) -> List[Dict[str, Any]]:
        """
        Processa a resposta da API e normaliza os dados.
        """
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("data", data.get("items", data.get("despesas", [])))
        else:
            return []

        despesas = []
        for item in items:
            despesa = {
                "numero_empenho": item.get("numero_empenho", item.get("empenho", "")),
                "ano": item.get("ano", ""),
                "data_empenho": item.get("data_empenho", ""),
                "data_liquidacao": item.get("data_liquidacao", ""),
                "data_pagamento": item.get("data_pagamento", ""),
                "valor_empenhado": self._parse_valor(item.get("valor_empenhado", 0)),
                "valor_liquidado": self._parse_valor(item.get("valor_liquidado", 0)),
                "valor_pago": self._parse_valor(item.get("valor_pago", 0)),
                "favorecido": item.get("favorecido", item.get("credor", "")),
                "cnpj_cpf": item.get("cnpj_cpf", item.get("documento", "")),
                "orgao": item.get("orgao", item.get("unidade_gestora", "")),
                "funcao": item.get("funcao", ""),
                "subfuncao": item.get("subfuncao", ""),
                "programa": item.get("programa", ""),
                "acao": item.get("acao", ""),
                "elemento_despesa": item.get("elemento_despesa", item.get("natureza", "")),
                "fonte_recurso": item.get("fonte_recurso", item.get("fonte", "")),
                "historico": item.get("historico", item.get("descricao", "")),
                "modalidade_licitacao": item.get("modalidade_licitacao", ""),
                "numero_licitacao": item.get("numero_licitacao", ""),
            }
            despesas.append(despesa)

        return despesas

    def _parse_valor(self, valor: Any) -> float:
        """
        Converte valor para float.
        """
        if isinstance(valor, (int, float)):
            return float(valor)
        if isinstance(valor, str):
            valor = valor.replace("R$", "").replace(".", "").replace(",", ".").strip()
            try:
                return float(valor)
            except ValueError:
                return 0.0
        return 0.0

    def collect_by_orgao(self, ano: int = None) -> Dict[str, float]:
        """
        Coleta totais de despesas agrupados por órgão.
        """
        despesas = self.collect(ano=ano)

        totais = {}
        for d in despesas:
            orgao = d.get("orgao", "Não informado")
            totais[orgao] = totais.get(orgao, 0) + d.get("valor_pago", 0)

        return dict(sorted(totais.items(), key=lambda x: x[1], reverse=True))

    def collect_by_favorecido(self, ano: int = None, top_n: int = 20) -> List[Dict]:
        """
        Retorna os maiores favorecidos (fornecedores/credores).
        """
        despesas = self.collect(ano=ano)

        totais = {}
        for d in despesas:
            fav = d.get("favorecido", "Não informado")
            cnpj = d.get("cnpj_cpf", "")
            key = (fav, cnpj)

            if key not in totais:
                totais[key] = {"favorecido": fav, "cnpj_cpf": cnpj, "valor_total": 0, "qtd_empenhos": 0}

            totais[key]["valor_total"] += d.get("valor_pago", 0)
            totais[key]["qtd_empenhos"] += 1

        ranking = sorted(totais.values(), key=lambda x: x["valor_total"], reverse=True)
        return ranking[:top_n]

    def detect_anomalies(self, ano: int = None, threshold_std: float = 2.0) -> List[Dict]:
        """
        Detecta despesas com valores atípicos (acima de N desvios padrão).
        """
        import statistics

        despesas = self.collect(ano=ano)
        valores = [d["valor_pago"] for d in despesas if d["valor_pago"] > 0]

        if len(valores) < 10:
            return []

        media = statistics.mean(valores)
        desvio = statistics.stdev(valores)
        limite = media + (threshold_std * desvio)

        anomalias = [d for d in despesas if d["valor_pago"] > limite]

        for a in anomalias:
            a["motivo_alerta"] = f"Valor {a['valor_pago']:.2f} acima do limite {limite:.2f}"
            a["desvios_acima"] = (a["valor_pago"] - media) / desvio if desvio > 0 else 0

        return sorted(anomalias, key=lambda x: x["valor_pago"], reverse=True)
