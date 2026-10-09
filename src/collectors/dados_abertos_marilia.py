"""
Coletor dos dados abertos do site da Prefeitura de Marília.

São conjuntos em JSON, um por tema e exercício, sem chave de acesso:

    https://www.marilia.sp.gov.br/portal/dados-abertos/{conjunto}/{ano}

A resposta é {"dados": [...]}. Um conjunto vazio vem como
{"dados": ["Nenhum registro encontrado."]}.

Mapa completo em APIS_MARILIA.md.
"""

import html
import logging
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)


class DadosAbertosMariliaCollector:
    """Conjuntos de dados abertos do site da Prefeitura de Marília."""

    BASE_URL = "https://www.marilia.sp.gov.br/portal/dados-abertos"

    CONJUNTOS = [
        "compra-direta",       # dispensas e inexigibilidades
        "contratos",           # contratos e atas de registro de preço
        "licitacoes",          # editais de licitação
        "chamamento-publico",
        "obras",
        "diario-oficial",      # texto integral de cada edição
        "legislacao",
        "concursos",
        "contas-publicas",
        "relatorio-viagens",
        "audiencias-publicas",
        "ouvidoria",
        "sic",
        "avaliacoes",
        "carta-servicos",
    ]

    # Campos que vêm com entidades HTML (&ccedil;, <br />).
    CAMPOS_HTML = ("descricao",)

    def __init__(self, timeout: int = 120):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "MonitoraMarilia/2.0 (MATRA - Controle Social)",
        })

    def get_conjunto(self, conjunto: str, ano: int) -> List[Dict]:
        """
        Registros de um conjunto no exercício.

        Returns:
            Lista de registros (vazia quando o portal responde "Nenhum registro encontrado.")
        """
        response = self.session.get(f"{self.BASE_URL}/{conjunto}/{ano}", timeout=self.timeout)
        response.raise_for_status()
        dados = response.json().get("dados")

        # Conjuntos agregados (sic, ouvidoria, avaliações) vêm como objeto, não como lista.
        if not isinstance(dados, list):
            return [dados] if dados else []

        registros = [r for r in dados if isinstance(r, dict)]
        for registro in registros:
            for campo in self.CAMPOS_HTML:
                if isinstance(registro.get(campo), str):
                    registro[campo] = html.unescape(registro[campo])

        logger.info("Dados abertos %s %s: %d registros", conjunto, ano, len(registros))
        return registros
