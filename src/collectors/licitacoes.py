"""
Coletor de dados de licitações do Portal de Transparência de Marília.

O portal SMARAPD usa JavaScript para renderizar os dados, então
utilizamos Playwright para obter o conteúdo dinâmico.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
from .base import BaseCollector
import logging
import re

logger = logging.getLogger(__name__)


class LicitacoesCollector(BaseCollector):
    """
    Coletor de licitações e processos licitatórios.
    Usa Playwright para acessar páginas com JavaScript.
    """

    def get_source_name(self) -> str:
        return "Licitações - Portal de Transparência de Marília"

    async def collect(
        self,
        ano: Optional[int] = None,
        limite: int = 100,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Coleta dados de licitações usando Playwright.

        Args:
            ano: Ano de referência (default: ano atual)
            limite: Número máximo de registros

        Returns:
            Lista de licitações
        """
        if ano is None:
            ano = datetime.now().year

        # Verificar cache primeiro
        cache_key = f"licitacoes_{ano}"
        cached = self._load_cache(cache_key, max_age_hours=12)
        if cached:
            return cached

        # URL do portal SMARAPD para licitações
        url = f"{self.BASE_URL}/#/licitacao"

        logger.info(f"Coletando licitações de {ano} via Playwright...")

        try:
            # Aguardar a tabela de licitações carregar
            html = await self._get_page_content(
                url,
                wait_selector="table, .table, .lista-licitacoes, .card",
                wait_time=8
            )

            if not html:
                logger.warning("Não foi possível obter conteúdo da página")
                return []

            licitacoes = await self._extract_licitacoes(html, ano)

            # Salvar no cache
            if licitacoes:
                self._save_cache(cache_key, licitacoes)

            logger.info(f"Coletadas {len(licitacoes)} licitações")
            return licitacoes[:limite]

        except Exception as e:
            logger.error(f"Erro ao coletar licitações: {e}")
            return []

    async def _extract_licitacoes(self, html: str, ano: int) -> List[Dict[str, Any]]:
        """
        Extrai dados de licitações do HTML renderizado.
        """
        soup = BeautifulSoup(html, "lxml")
        licitacoes = []

        # Tentar extrair de tabelas
        table_data = await self._extract_table_data(html, "table")
        if table_data:
            for row in table_data:
                licitacao = self._normalize_licitacao(row, ano)
                if licitacao:
                    licitacoes.append(licitacao)

        # Se não encontrou em tabelas, tentar cards/divs
        if not licitacoes:
            cards = soup.select(".card, .licitacao-item, .item-lista, [class*='licitacao']")
            for card in cards:
                licitacao = self._extract_from_card(card, ano)
                if licitacao:
                    licitacoes.append(licitacao)

        # Filtrar pelo ano se especificado
        if ano:
            licitacoes = [
                l for l in licitacoes
                if str(ano) in str(l.get("numero", "")) or
                   str(ano) in str(l.get("ano", "")) or
                   str(ano) in str(l.get("data_abertura", ""))
            ]

        return licitacoes

    def _normalize_licitacao(self, row: Dict, ano: int) -> Optional[Dict[str, Any]]:
        """
        Normaliza dados de uma licitação extraída.
        """
        # Mapear campos comuns
        numero = (
            row.get("numero") or
            row.get("numero_licitacao") or
            row.get("num") or
            row.get("processo") or
            ""
        )

        if not numero:
            return None

        return {
            "numero": numero,
            "ano": row.get("ano", ano),
            "modalidade": row.get("modalidade", row.get("tipo", "")),
            "objeto": row.get("objeto", row.get("descricao", "")),
            "valor_estimado": self._parse_currency(
                row.get("valor_estimado", row.get("valor", "0"))
            ),
            "valor_homologado": self._parse_currency(
                row.get("valor_homologado", "0")
            ),
            "data_abertura": self._parse_date(
                row.get("data_abertura", row.get("data", ""))
            ),
            "data_homologacao": self._parse_date(
                row.get("data_homologacao", "")
            ),
            "status": row.get("status", row.get("situacao", "")),
            "orgao": row.get("orgao", row.get("unidade", "")),
        }

    def _extract_from_card(self, card, ano: int) -> Optional[Dict[str, Any]]:
        """
        Extrai dados de licitação de um elemento card/div.
        """
        text = card.get_text(separator=" ", strip=True)

        # Tentar extrair número da licitação com regex
        numero_match = re.search(
            r'(PE|PP|CC|TP|CV|DL|IN)[\s\-]*(\d+)[/\-]?(\d{4})?',
            text,
            re.IGNORECASE
        )
        if not numero_match:
            return None

        modalidades = {
            "PE": "Pregão Eletrônico",
            "PP": "Pregão Presencial",
            "CC": "Concorrência",
            "TP": "Tomada de Preços",
            "CV": "Convite",
            "DL": "Dispensa",
            "IN": "Inexigibilidade"
        }

        tipo = numero_match.group(1).upper()
        numero = numero_match.group(2)
        ano_lic = numero_match.group(3) or str(ano)

        # Extrair valor se presente
        valor_match = re.search(r'R\$\s*([\d.,]+)', text)
        valor = valor_match.group(1) if valor_match else "0"

        # Extrair data se presente
        data_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
        data = data_match.group(1) if data_match else ""

        return {
            "numero": f"{tipo} {numero}/{ano_lic}",
            "ano": ano_lic,
            "modalidade": modalidades.get(tipo, tipo),
            "objeto": text[:200] if len(text) > 200 else text,
            "valor_estimado": self._parse_currency(valor),
            "valor_homologado": 0.0,
            "data_abertura": self._parse_date(data),
            "data_homologacao": None,
            "status": "",
            "orgao": "",
        }

    async def collect_recentes(self, limite: int = 10) -> List[Dict[str, Any]]:
        """
        Coleta as licitações mais recentes.
        """
        licitacoes = await self.collect(limite=limite)
        # Ordenar por data
        return sorted(
            licitacoes,
            key=lambda x: x.get("data_abertura") or "",
            reverse=True
        )[:limite]
