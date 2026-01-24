"""
Coletor de dados de contratos do Portal de Transparência de Marília.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from .base import BaseCollector
import logging

logger = logging.getLogger(__name__)


class ContratosCollector(BaseCollector):
    """
    Coletor de contratos administrativos.
    """

    ENDPOINT = "/api/contratos"

    def get_source_name(self) -> str:
        return "Contratos - Portal de Transparência de Marília"

    def collect(
        self,
        ano: Optional[int] = None,
        status: Optional[str] = None,
        fornecedor: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Coleta dados de contratos.

        Args:
            ano: Ano de referência
            status: Filtrar por status (vigente, encerrado, etc.)
            fornecedor: Filtrar por nome ou CNPJ do fornecedor

        Returns:
            Lista de contratos
        """
        if ano is None:
            ano = datetime.now().year

        url = f"{self.BASE_URL}{self.ENDPOINT}"
        params = {"ano": ano}

        if status:
            params["status"] = status
        if fornecedor:
            params["fornecedor"] = fornecedor

        logger.info(f"Coletando contratos de {ano}...")

        response = self._make_request(url, params=params)

        if response is None:
            logger.warning("API não disponível")
            return []

        try:
            data = response.json()
            contratos = self._parse_response(data)
            logger.info(f"Coletados {len(contratos)} contratos")
            return contratos
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
            items = data.get("data", data.get("items", data.get("contratos", [])))
        else:
            return []

        contratos = []
        for item in items:
            contrato = {
                "numero": item.get("numero", item.get("num_contrato", "")),
                "ano": item.get("ano", ""),
                "objeto": item.get("objeto", item.get("descricao", "")),
                "fornecedor": item.get("fornecedor", item.get("contratado", "")),
                "cnpj": item.get("cnpj", item.get("cnpj_contratado", "")),
                "valor_original": self._parse_valor(item.get("valor_original", 0)),
                "valor_aditivos": self._parse_valor(item.get("valor_aditivos", 0)),
                "valor_atual": self._parse_valor(item.get("valor_atual", 0)),
                "data_assinatura": item.get("data_assinatura", ""),
                "data_inicio": item.get("data_inicio", item.get("vigencia_inicio", "")),
                "data_fim": item.get("data_fim", item.get("vigencia_fim", "")),
                "status": item.get("status", item.get("situacao", "")),
                "modalidade_licitacao": item.get("modalidade_licitacao", ""),
                "numero_licitacao": item.get("numero_licitacao", ""),
                "orgao": item.get("orgao", item.get("unidade", "")),
                "qtd_aditivos": item.get("qtd_aditivos", 0),
                "url_contrato": item.get("url_contrato", item.get("link", "")),
            }

            # Calcular percentual de aditivos
            if contrato["valor_original"] > 0:
                contrato["percentual_aditivos"] = (
                    contrato["valor_aditivos"] / contrato["valor_original"]
                ) * 100
            else:
                contrato["percentual_aditivos"] = 0

            contratos.append(contrato)

        return contratos

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

    def collect_vigentes(self) -> List[Dict[str, Any]]:
        """
        Coleta apenas contratos vigentes.
        """
        return self.collect(status="vigente")

    def detect_aditivos_excessivos(self, limite_percentual: float = 25.0) -> List[Dict]:
        """
        Detecta contratos com aditivos acima do limite legal (25%).

        Args:
            limite_percentual: Percentual limite para alerta (padrão 25%)

        Returns:
            Lista de contratos com aditivos excessivos
        """
        contratos = self.collect()

        irregulares = [
            c for c in contratos
            if c["percentual_aditivos"] > limite_percentual
        ]

        for c in irregulares:
            c["motivo_alerta"] = (
                f"Aditivo de {c['percentual_aditivos']:.1f}% "
                f"excede o limite de {limite_percentual}%"
            )

        return sorted(irregulares, key=lambda x: x["percentual_aditivos"], reverse=True)

    def detect_dispensas_valor_alto(self, limite_valor: float = 50000.0) -> List[Dict]:
        """
        Detecta contratos por dispensa de licitação com valor elevado.

        Args:
            limite_valor: Valor limite para alerta

        Returns:
            Lista de contratos suspeitos
        """
        contratos = self.collect()

        suspeitos = [
            c for c in contratos
            if c["modalidade_licitacao"].lower() in ["dispensa", "dl"]
            and c["valor_atual"] > limite_valor
        ]

        for c in suspeitos:
            c["motivo_alerta"] = (
                f"Dispensa de licitação no valor de R$ {c['valor_atual']:,.2f}"
            )

        return sorted(suspeitos, key=lambda x: x["valor_atual"], reverse=True)

    def analyze_fornecedor_concentracao(self, top_n: int = 10) -> List[Dict]:
        """
        Analisa concentração de contratos por fornecedor.
        """
        contratos = self.collect()

        totais = {}
        for c in contratos:
            forn = c.get("fornecedor", "Não informado")
            cnpj = c.get("cnpj", "")
            key = (forn, cnpj)

            if key not in totais:
                totais[key] = {
                    "fornecedor": forn,
                    "cnpj": cnpj,
                    "valor_total": 0,
                    "qtd_contratos": 0,
                    "contratos": []
                }

            totais[key]["valor_total"] += c.get("valor_atual", 0)
            totais[key]["qtd_contratos"] += 1
            totais[key]["contratos"].append(c.get("numero", ""))

        ranking = sorted(totais.values(), key=lambda x: x["valor_total"], reverse=True)
        return ranking[:top_n]
