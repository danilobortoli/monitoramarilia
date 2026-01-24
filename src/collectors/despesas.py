"""
Coletor de dados de despesas do Portal de Transparência de Marília.

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


class DespesasCollector(BaseCollector):
    """
    Coletor de despesas públicas (empenho, liquidação, pagamento).
    Usa Playwright para acessar páginas com JavaScript.
    """

    def get_source_name(self) -> str:
        return "Despesas - Portal de Transparência de Marília"

    async def collect(
        self,
        ano: Optional[int] = None,
        mes: Optional[int] = None,
        limite: int = 100,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Coleta dados de despesas usando Playwright.

        Args:
            ano: Ano de referência
            mes: Mês de referência (1-12)
            limite: Número máximo de registros

        Returns:
            Lista de despesas
        """
        if ano is None:
            ano = datetime.now().year

        # Verificar cache primeiro
        cache_key = f"despesas_{ano}_{mes or 'all'}"
        cached = self._load_cache(cache_key, max_age_hours=6)
        if cached:
            return cached

        # URL do portal SMARAPD para despesas
        url = f"{self.BASE_URL}/#/despesa"

        logger.info(f"Coletando despesas de {mes or 'todos os meses'}/{ano} via Playwright...")

        try:
            html = await self._get_page_content(
                url,
                wait_selector="table, .table, .lista-despesas, .card",
                wait_time=8
            )

            if not html:
                logger.warning("Não foi possível obter conteúdo da página")
                return []

            despesas = await self._extract_despesas(html, ano, mes)

            # Salvar no cache
            if despesas:
                self._save_cache(cache_key, despesas)

            logger.info(f"Coletadas {len(despesas)} despesas")
            return despesas[:limite]

        except Exception as e:
            logger.error(f"Erro ao coletar despesas: {e}")
            return []

    async def _extract_despesas(self, html: str, ano: int, mes: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Extrai dados de despesas do HTML renderizado.
        """
        soup = BeautifulSoup(html, "lxml")
        despesas = []

        # Tentar extrair de tabelas
        table_data = await self._extract_table_data(html, "table")
        if table_data:
            for row in table_data:
                despesa = self._normalize_despesa(row, ano)
                if despesa:
                    despesas.append(despesa)

        # Se não encontrou em tabelas, tentar cards/divs
        if not despesas:
            cards = soup.select(".card, .despesa-item, .item-lista, [class*='despesa']")
            for card in cards:
                despesa = self._extract_from_card(card, ano)
                if despesa:
                    despesas.append(despesa)

        return despesas

    def _normalize_despesa(self, row: Dict, ano: int) -> Optional[Dict[str, Any]]:
        """
        Normaliza dados de uma despesa extraída.
        """
        numero = (
            row.get("numero_empenho") or
            row.get("empenho") or
            row.get("numero") or
            ""
        )

        valor_empenhado = self._parse_currency(
            row.get("valor_empenhado", row.get("empenhado", "0"))
        )
        valor_liquidado = self._parse_currency(
            row.get("valor_liquidado", row.get("liquidado", "0"))
        )
        valor_pago = self._parse_currency(
            row.get("valor_pago", row.get("pago", row.get("valor", "0")))
        )

        return {
            "numero_empenho": numero,
            "ano": row.get("ano", ano),
            "data_empenho": self._parse_date(row.get("data_empenho", row.get("data", ""))),
            "data_liquidacao": self._parse_date(row.get("data_liquidacao", "")),
            "data_pagamento": self._parse_date(row.get("data_pagamento", "")),
            "valor_empenhado": valor_empenhado,
            "valor_liquidado": valor_liquidado,
            "valor_pago": valor_pago,
            "favorecido": row.get("favorecido", row.get("credor", row.get("fornecedor", ""))),
            "cnpj_cpf": row.get("cnpj_cpf", row.get("cnpj", row.get("documento", ""))),
            "orgao": row.get("orgao", row.get("unidade_gestora", row.get("unidade", ""))),
            "funcao": row.get("funcao", ""),
            "subfuncao": row.get("subfuncao", ""),
            "elemento_despesa": row.get("elemento_despesa", row.get("natureza", "")),
            "fonte_recurso": row.get("fonte_recurso", row.get("fonte", "")),
            "historico": row.get("historico", row.get("descricao", "")),
        }

    def _extract_from_card(self, card, ano: int) -> Optional[Dict[str, Any]]:
        """
        Extrai dados de despesa de um elemento card/div.
        """
        text = card.get_text(separator=" ", strip=True)

        # Extrair valor
        valor_match = re.search(r'R\$\s*([\d.,]+)', text)
        if not valor_match:
            return None

        valor = valor_match.group(1)

        # Extrair CNPJ/CPF
        cnpj_match = re.search(r'\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2}', text)
        documento = cnpj_match.group(0) if cnpj_match else ""

        # Extrair data
        data_match = re.search(r'(\d{2}/\d{2}/\d{4})', text)
        data = data_match.group(1) if data_match else ""

        return {
            "numero_empenho": "",
            "ano": ano,
            "data_empenho": self._parse_date(data),
            "data_liquidacao": None,
            "data_pagamento": None,
            "valor_empenhado": self._parse_currency(valor),
            "valor_liquidado": 0.0,
            "valor_pago": self._parse_currency(valor),
            "favorecido": "",
            "cnpj_cpf": documento,
            "orgao": "",
            "funcao": "",
            "subfuncao": "",
            "elemento_despesa": "",
            "fonte_recurso": "",
            "historico": text[:200] if len(text) > 200 else text,
        }

    async def collect_totais_mensais(self, ano: Optional[int] = None) -> Dict[str, Dict[str, float]]:
        """
        Coleta totais de despesas por mês (empenhado, liquidado, pago).
        """
        if ano is None:
            ano = datetime.now().year

        despesas = await self.collect(ano=ano, limite=10000)

        meses = {}
        for d in despesas:
            data = d.get("data_empenho") or ""
            if data:
                # Extrair mês da data
                try:
                    mes = int(data.split("-")[1])
                except (IndexError, ValueError):
                    continue

                if mes not in meses:
                    meses[mes] = {"empenhado": 0, "liquidado": 0, "pago": 0}

                meses[mes]["empenhado"] += d.get("valor_empenhado", 0)
                meses[mes]["liquidado"] += d.get("valor_liquidado", 0)
                meses[mes]["pago"] += d.get("valor_pago", 0)

        return meses

    async def collect_by_favorecido(self, ano: Optional[int] = None, top_n: int = 20) -> List[Dict]:
        """
        Retorna os maiores favorecidos (fornecedores/credores).
        """
        despesas = await self.collect(ano=ano, limite=10000)

        totais = {}
        valor_total_geral = sum(d.get("valor_pago", 0) for d in despesas)

        for d in despesas:
            fav = d.get("favorecido") or "Não informado"
            cnpj = d.get("cnpj_cpf", "")
            key = (fav, cnpj)

            if key not in totais:
                totais[key] = {
                    "favorecido": fav,
                    "cnpj_cpf": cnpj,
                    "valor_total": 0,
                    "qtd_empenhos": 0
                }

            totais[key]["valor_total"] += d.get("valor_pago", 0)
            totais[key]["qtd_empenhos"] += 1

        # Calcular percentual
        for data in totais.values():
            if valor_total_geral > 0:
                data["percentual_total"] = (data["valor_total"] / valor_total_geral) * 100
            else:
                data["percentual_total"] = 0

        ranking = sorted(totais.values(), key=lambda x: x["valor_total"], reverse=True)
        return ranking[:top_n]

    async def detect_fracionamento(self, ano: Optional[int] = None, limite_valor: float = 80000) -> List[Dict]:
        """
        Detecta possível fracionamento de despesas.
        Agrupa despesas do mesmo favorecido no mesmo mês e verifica
        se o total ultrapassa o limite de dispensa.
        """
        despesas = await self.collect(ano=ano, limite=10000)

        # Agrupar por favorecido e mês
        grupos = {}
        for d in despesas:
            fav = d.get("favorecido", "")
            data = d.get("data_empenho", "")
            if not fav or not data:
                continue

            try:
                mes_ano = data[:7]  # YYYY-MM
            except:
                continue

            key = (fav, mes_ano)
            if key not in grupos:
                grupos[key] = {
                    "favorecido": fav,
                    "mes": mes_ano,
                    "despesas": [],
                    "valor_total": 0
                }

            grupos[key]["despesas"].append(d)
            grupos[key]["valor_total"] += d.get("valor_pago", 0)

        # Filtrar grupos suspeitos (muitas despesas pequenas totalizando valor alto)
        suspeitos = []
        for key, grupo in grupos.items():
            if (
                len(grupo["despesas"]) >= 3 and
                grupo["valor_total"] > limite_valor
            ):
                grupo["motivo_alerta"] = (
                    f"Possível fracionamento: {len(grupo['despesas'])} despesas "
                    f"totalizando R$ {grupo['valor_total']:,.2f} no mês {grupo['mes']}"
                )
                grupo["tipo"] = "critico"
                suspeitos.append(grupo)

        return sorted(suspeitos, key=lambda x: x["valor_total"], reverse=True)
