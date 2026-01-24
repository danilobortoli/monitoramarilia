"""
Coletor de dados de contratos do Portal de Transparência de Marília.

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


class ContratosCollector(BaseCollector):
    """
    Coletor de contratos administrativos.
    Usa Playwright para acessar páginas com JavaScript.
    """

    def get_source_name(self) -> str:
        return "Contratos - Portal de Transparência de Marília"

    async def collect(
        self,
        ano: Optional[int] = None,
        limite: int = 100,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Coleta dados de contratos usando Playwright.

        Args:
            ano: Ano de referência
            limite: Número máximo de registros

        Returns:
            Lista de contratos
        """
        if ano is None:
            ano = datetime.now().year

        # Verificar cache primeiro
        cache_key = f"contratos_{ano}"
        cached = self._load_cache(cache_key, max_age_hours=12)
        if cached:
            return cached

        # URL do portal SMARAPD para contratos
        url = f"{self.BASE_URL}/#/contrato"

        logger.info(f"Coletando contratos de {ano} via Playwright...")

        try:
            html = await self._get_page_content(
                url,
                wait_selector="table, .table, .lista-contratos, .card",
                wait_time=8
            )

            if not html:
                logger.warning("Não foi possível obter conteúdo da página")
                return []

            contratos = await self._extract_contratos(html, ano)

            # Salvar no cache
            if contratos:
                self._save_cache(cache_key, contratos)

            logger.info(f"Coletados {len(contratos)} contratos")
            return contratos[:limite]

        except Exception as e:
            logger.error(f"Erro ao coletar contratos: {e}")
            return []

    async def _extract_contratos(self, html: str, ano: int) -> List[Dict[str, Any]]:
        """
        Extrai dados de contratos do HTML renderizado.
        """
        soup = BeautifulSoup(html, "lxml")
        contratos = []

        # Tentar extrair de tabelas
        table_data = await self._extract_table_data(html, "table")
        if table_data:
            for row in table_data:
                contrato = self._normalize_contrato(row, ano)
                if contrato:
                    contratos.append(contrato)

        # Se não encontrou em tabelas, tentar cards/divs
        if not contratos:
            cards = soup.select(".card, .contrato-item, .item-lista, [class*='contrato']")
            for card in cards:
                contrato = self._extract_from_card(card, ano)
                if contrato:
                    contratos.append(contrato)

        return contratos

    def _normalize_contrato(self, row: Dict, ano: int) -> Optional[Dict[str, Any]]:
        """
        Normaliza dados de um contrato extraído.
        """
        numero = (
            row.get("numero") or
            row.get("numero_contrato") or
            row.get("num") or
            row.get("contrato") or
            ""
        )

        if not numero:
            return None

        valor_original = self._parse_currency(
            row.get("valor_original", row.get("valor", "0"))
        )
        valor_aditivos = self._parse_currency(
            row.get("valor_aditivos", row.get("aditivo", "0"))
        )
        valor_atual = self._parse_currency(
            row.get("valor_atual", row.get("valor_total", "0"))
        )

        if valor_atual == 0 and valor_original > 0:
            valor_atual = valor_original + valor_aditivos

        percentual_aditivos = 0
        if valor_original > 0:
            percentual_aditivos = (valor_aditivos / valor_original) * 100

        return {
            "numero": numero,
            "ano": row.get("ano", ano),
            "objeto": row.get("objeto", row.get("descricao", "")),
            "fornecedor": row.get("fornecedor", row.get("contratado", "")),
            "cnpj": row.get("cnpj", row.get("cnpj_contratado", "")),
            "valor_original": valor_original,
            "valor_aditivos": valor_aditivos,
            "valor_atual": valor_atual,
            "percentual_aditivos": percentual_aditivos,
            "data_assinatura": self._parse_date(row.get("data_assinatura", "")),
            "data_inicio": self._parse_date(row.get("data_inicio", row.get("vigencia_inicio", ""))),
            "data_fim": self._parse_date(row.get("data_fim", row.get("vigencia_fim", ""))),
            "status": row.get("status", row.get("situacao", "")),
            "modalidade_licitacao": row.get("modalidade_licitacao", row.get("modalidade", "")),
            "orgao": row.get("orgao", row.get("unidade", "")),
        }

    def _extract_from_card(self, card, ano: int) -> Optional[Dict[str, Any]]:
        """
        Extrai dados de contrato de um elemento card/div.
        """
        text = card.get_text(separator=" ", strip=True)

        # Tentar extrair número do contrato
        numero_match = re.search(
            r'[Cc]ontrato[\s\-nº]*(\d+)[/\-]?(\d{4})?',
            text
        )
        if not numero_match:
            return None

        numero = numero_match.group(1)
        ano_contrato = numero_match.group(2) or str(ano)

        # Extrair valor
        valor_match = re.search(r'R\$\s*([\d.,]+)', text)
        valor = valor_match.group(1) if valor_match else "0"

        # Extrair CNPJ
        cnpj_match = re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}', text)
        cnpj = cnpj_match.group(0) if cnpj_match else ""

        return {
            "numero": f"{numero}/{ano_contrato}",
            "ano": ano_contrato,
            "objeto": text[:200] if len(text) > 200 else text,
            "fornecedor": "",
            "cnpj": cnpj,
            "valor_original": self._parse_currency(valor),
            "valor_aditivos": 0.0,
            "valor_atual": self._parse_currency(valor),
            "percentual_aditivos": 0,
            "data_assinatura": None,
            "data_inicio": None,
            "data_fim": None,
            "status": "",
            "modalidade_licitacao": "",
            "orgao": "",
        }

    async def detect_aditivos_excessivos(self, limite_percentual: float = 25.0) -> List[Dict]:
        """
        Detecta contratos com aditivos acima do limite legal (25%).
        """
        contratos = await self.collect()

        irregulares = [
            c for c in contratos
            if c.get("percentual_aditivos", 0) > limite_percentual
        ]

        for c in irregulares:
            c["motivo_alerta"] = (
                f"Aditivo de {c['percentual_aditivos']:.1f}% "
                f"excede o limite de {limite_percentual}%"
            )
            c["tipo"] = "critico"

        return sorted(irregulares, key=lambda x: x["percentual_aditivos"], reverse=True)

    async def detect_dispensas_valor_alto(self, limite_valor: float = 50000.0) -> List[Dict]:
        """
        Detecta contratos por dispensa de licitação com valor elevado.
        """
        contratos = await self.collect()

        suspeitos = [
            c for c in contratos
            if c.get("modalidade_licitacao", "").lower() in ["dispensa", "dl"]
            and c.get("valor_atual", 0) > limite_valor
        ]

        for c in suspeitos:
            c["motivo_alerta"] = (
                f"Dispensa de licitação no valor de R$ {c['valor_atual']:,.2f}"
            )
            c["tipo"] = "critico"

        return sorted(suspeitos, key=lambda x: x["valor_atual"], reverse=True)

    async def analyze_fornecedor_concentracao(self, top_n: int = 10) -> List[Dict]:
        """
        Analisa concentração de contratos por fornecedor.
        """
        contratos = await self.collect()

        totais = {}
        valor_total_geral = sum(c.get("valor_atual", 0) for c in contratos)

        for c in contratos:
            forn = c.get("fornecedor") or "Não informado"
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

        # Calcular percentual de cada fornecedor
        for key, data in totais.items():
            if valor_total_geral > 0:
                data["percentual_total"] = (data["valor_total"] / valor_total_geral) * 100
            else:
                data["percentual_total"] = 0

        ranking = sorted(totais.values(), key=lambda x: x["valor_total"], reverse=True)
        return ranking[:top_n]
