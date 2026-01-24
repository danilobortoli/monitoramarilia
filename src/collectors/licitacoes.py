"""
Coletor de dados de licitações do Portal de Transparência de Marília.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from .base import BaseCollector
import logging

logger = logging.getLogger(__name__)


class LicitacoesCollector(BaseCollector):
    """
    Coletor de licitações e processos licitatórios.
    """

    ENDPOINT = "/api/licitacoes"

    def get_source_name(self) -> str:
        return "Licitações - Portal de Transparência de Marília"

    def collect(
        self,
        ano: Optional[int] = None,
        modalidade: Optional[str] = None,
        status: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Coleta dados de licitações.

        Args:
            ano: Ano de referência (default: ano atual)
            modalidade: Filtrar por modalidade (pregao, concorrencia, etc.)
            status: Filtrar por status (em_andamento, homologada, etc.)

        Returns:
            Lista de licitações
        """
        if ano is None:
            ano = datetime.now().year

        url = f"{self.BASE_URL}{self.ENDPOINT}"
        params = {
            "ano": ano,
        }

        if modalidade:
            params["modalidade"] = modalidade
        if status:
            params["status"] = status

        logger.info(f"Coletando licitações de {ano}...")

        # Tentativa de acesso à API
        response = self._make_request(url, params=params)

        if response is None:
            logger.warning("API não disponível, tentando scraping HTML...")
            return self._collect_from_html(ano)

        try:
            data = response.json()
            licitacoes = self._parse_response(data)
            logger.info(f"Coletadas {len(licitacoes)} licitações")
            return licitacoes
        except Exception as e:
            logger.error(f"Erro ao processar resposta: {e}")
            return []

    def _collect_from_html(self, ano: int) -> List[Dict[str, Any]]:
        """
        Coleta dados via scraping HTML quando API não está disponível.
        """
        # URL alternativa para página HTML
        url = f"{self.BASE_URL}/#/licitacoes?ano={ano}"

        # Placeholder - implementar scraping real com BeautifulSoup/Selenium
        logger.info(f"Scraping HTML de {url}")

        return []

    def _parse_response(self, data: Any) -> List[Dict[str, Any]]:
        """
        Processa a resposta da API e normaliza os dados.
        """
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("data", data.get("items", data.get("licitacoes", [])))
        else:
            return []

        licitacoes = []
        for item in items:
            licitacao = {
                "numero": item.get("numero", item.get("num_licitacao", "")),
                "ano": item.get("ano", ""),
                "modalidade": item.get("modalidade", ""),
                "objeto": item.get("objeto", item.get("descricao", "")),
                "valor_estimado": self._parse_valor(item.get("valor_estimado", 0)),
                "valor_homologado": self._parse_valor(item.get("valor_homologado", 0)),
                "data_abertura": item.get("data_abertura", ""),
                "data_homologacao": item.get("data_homologacao", ""),
                "status": item.get("status", item.get("situacao", "")),
                "orgao": item.get("orgao", item.get("unidade", "")),
                "vencedor": item.get("vencedor", item.get("fornecedor", "")),
                "cnpj_vencedor": item.get("cnpj_vencedor", ""),
                "url_edital": item.get("url_edital", item.get("link_edital", "")),
            }
            licitacoes.append(licitacao)

        return licitacoes

    def _parse_valor(self, valor: Any) -> float:
        """
        Converte valor para float.
        """
        if isinstance(valor, (int, float)):
            return float(valor)
        if isinstance(valor, str):
            # Remove formatação brasileira
            valor = valor.replace("R$", "").replace(".", "").replace(",", ".").strip()
            try:
                return float(valor)
            except ValueError:
                return 0.0
        return 0.0

    def collect_by_modalidade(self, ano: int = None) -> Dict[str, List[Dict]]:
        """
        Coleta licitações agrupadas por modalidade.
        """
        if ano is None:
            ano = datetime.now().year

        modalidades = [
            "pregao_eletronico",
            "pregao_presencial",
            "concorrencia",
            "tomada_precos",
            "convite",
            "dispensa",
            "inexigibilidade"
        ]

        resultado = {}
        for mod in modalidades:
            resultado[mod] = self.collect(ano=ano, modalidade=mod)

        return resultado
