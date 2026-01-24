"""
Coletor de dados de receitas do Portal de Transparência de Marília.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from .base import BaseCollector
import logging

logger = logging.getLogger(__name__)


class ReceitasCollector(BaseCollector):
    """
    Coletor de receitas públicas.
    """

    ENDPOINT = "/api/receitas"

    def get_source_name(self) -> str:
        return "Receitas - Portal de Transparência de Marília"

    def collect(
        self,
        ano: Optional[int] = None,
        mes: Optional[int] = None,
        fonte: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Coleta dados de receitas.

        Args:
            ano: Ano de referência
            mes: Mês de referência
            fonte: Filtrar por fonte de recurso

        Returns:
            Lista de receitas
        """
        if ano is None:
            ano = datetime.now().year

        url = f"{self.BASE_URL}{self.ENDPOINT}"
        params = {"ano": ano}

        if mes:
            params["mes"] = mes
        if fonte:
            params["fonte"] = fonte

        logger.info(f"Coletando receitas de {ano}...")

        response = self._make_request(url, params=params)

        if response is None:
            logger.warning("API não disponível")
            return []

        try:
            data = response.json()
            return self._parse_response(data)
        except Exception as e:
            logger.error(f"Erro ao processar resposta: {e}")
            return []

    def _parse_response(self, data: Any) -> List[Dict[str, Any]]:
        """
        Processa a resposta da API.
        """
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("data", data.get("receitas", []))
        else:
            return []

        receitas = []
        for item in items:
            receita = {
                "ano": item.get("ano", ""),
                "mes": item.get("mes", ""),
                "categoria": item.get("categoria", item.get("tipo", "")),
                "origem": item.get("origem", ""),
                "especie": item.get("especie", ""),
                "rubrica": item.get("rubrica", ""),
                "alinea": item.get("alinea", ""),
                "subalinea": item.get("subalinea", ""),
                "descricao": item.get("descricao", item.get("especificacao", "")),
                "valor_previsto": self._parse_valor(item.get("valor_previsto", 0)),
                "valor_arrecadado": self._parse_valor(item.get("valor_arrecadado", 0)),
                "fonte_recurso": item.get("fonte_recurso", item.get("fonte", "")),
            }
            receitas.append(receita)

        return receitas

    def _parse_valor(self, valor: Any) -> float:
        if isinstance(valor, (int, float)):
            return float(valor)
        if isinstance(valor, str):
            valor = valor.replace("R$", "").replace(".", "").replace(",", ".").strip()
            try:
                return float(valor)
            except ValueError:
                return 0.0
        return 0.0

    def collect_by_categoria(self, ano: int = None) -> Dict[str, float]:
        """
        Coleta receitas agrupadas por categoria.
        """
        receitas = self.collect(ano=ano)

        totais = {}
        for r in receitas:
            cat = r.get("categoria", "Não informado")
            totais[cat] = totais.get(cat, 0) + r.get("valor_arrecadado", 0)

        return dict(sorted(totais.items(), key=lambda x: x[1], reverse=True))
