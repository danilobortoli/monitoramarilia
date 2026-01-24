"""
Coletor de dados do TCE-SP - Tribunal de Contas do Estado de São Paulo.

APIs do Portal de Transparência Municipal do TCE-SP.
Fonte oficial com dados detalhados de despesas, receitas, licitações.

APIs: https://transparencia.tce.sp.gov.br/apis
Dados: https://transparencia.tce.sp.gov.br/conjunto-de-dados
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class TCESPCollector:
    """
    Coletor de dados via APIs do TCE-SP.

    Coleta:
    - Despesas detalhadas (empenho, liquidação, pagamento)
    - Receitas
    - Licitações (Fase IV AUDESP)
    - Contratos
    """

    BASE_URL = "https://transparencia.tce.sp.gov.br/api/json"
    MUNICIPIO = "marilia"

    def __init__(self, timeout: int = 60):
        """
        Inicializa o coletor TCE-SP.

        Args:
            timeout: Tempo máximo de espera por requisição
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "MonitoraMarilia/2.0 (MATRA - Controle Social)"
        })

    def _make_request(self, endpoint: str) -> Optional[List[Dict]]:
        """
        Faz requisição à API TCE-SP.

        Args:
            endpoint: Endpoint da API

        Returns:
            Lista de dados ou None em caso de falha
        """
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            logger.info(f"TCE-SP: {endpoint}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            return data if isinstance(data, list) else [data] if data else []

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição TCE-SP: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao processar resposta TCE-SP: {e}")
            return None

    def get_despesas(self, ano: int, mes: int) -> List[Dict[str, Any]]:
        """
        Busca despesas detalhadas de um mês.

        Dados retornados:
        - Órgão, unidade orçamentária
        - Evento (empenhado, liquidado, pago, anulado)
        - Número do empenho
        - Fornecedor (CNPJ parcial)
        - Data e valor

        Args:
            ano: Ano de referência
            mes: Mês (1-12)

        Returns:
            Lista de despesas
        """
        endpoint = f"despesas/{self.MUNICIPIO}/{ano}/{mes}"
        data = self._make_request(endpoint)

        if not data:
            return []

        # Normalizar dados
        despesas = []
        for item in data:
            despesas.append({
                "orgao": item.get("orgao", ""),
                "unidade": item.get("unidadeorcamentaria", ""),
                "mes": item.get("mes", mes),
                "evento": item.get("evento", ""),  # EMPENHADO, LIQUIDADO, PAGO
                "numero_empenho": item.get("numeroempenho", ""),
                "fornecedor": item.get("fornecedor", ""),
                "cnpj_parcial": item.get("cnpj", ""),
                "data": item.get("data", ""),
                "valor": self._parse_valor(item.get("valor", 0)),
                "fonte": "TCE-SP"
            })

        return despesas

    def get_despesas_ano(self, ano: int) -> List[Dict[str, Any]]:
        """
        Busca despesas de todo o ano.

        Args:
            ano: Ano de referência

        Returns:
            Lista de despesas do ano
        """
        todas_despesas = []

        for mes in range(1, 13):
            logger.info(f"Coletando despesas {mes}/{ano}...")
            despesas_mes = self.get_despesas(ano, mes)
            todas_despesas.extend(despesas_mes)

        logger.info(f"Total coletado: {len(todas_despesas)} despesas de {ano}")
        return todas_despesas

    def get_receitas(self, ano: int, mes: int) -> List[Dict[str, Any]]:
        """
        Busca receitas de um mês.

        Args:
            ano: Ano de referência
            mes: Mês (1-12)

        Returns:
            Lista de receitas
        """
        endpoint = f"receitas/{self.MUNICIPIO}/{ano}/{mes}"
        data = self._make_request(endpoint)

        if not data:
            return []

        receitas = []
        for item in data:
            receitas.append({
                "orgao": item.get("orgao", ""),
                "mes": item.get("mes", mes),
                "categoria": item.get("categoria", ""),
                "origem": item.get("origem", ""),
                "especie": item.get("especie", ""),
                "rubrica": item.get("rubrica", ""),
                "valor_previsto": self._parse_valor(item.get("valorprevisto", 0)),
                "valor_arrecadado": self._parse_valor(item.get("valorarrecadado", 0)),
                "fonte": "TCE-SP"
            })

        return receitas

    def get_maiores_fornecedores(self, ano: int, top_n: int = 20) -> List[Dict[str, Any]]:
        """
        Identifica os maiores fornecedores do ano.

        Args:
            ano: Ano de referência
            top_n: Quantidade de fornecedores a retornar

        Returns:
            Lista dos maiores fornecedores
        """
        despesas = self.get_despesas_ano(ano)

        # Filtrar apenas pagamentos
        pagamentos = [d for d in despesas if "PAGO" in d.get("evento", "").upper()]

        # Agrupar por fornecedor
        totais = {}
        for d in pagamentos:
            fornecedor = d.get("fornecedor", "Não informado")
            cnpj = d.get("cnpj_parcial", "")
            key = (fornecedor, cnpj)

            if key not in totais:
                totais[key] = {
                    "fornecedor": fornecedor,
                    "cnpj_parcial": cnpj,
                    "valor_total": 0,
                    "qtd_pagamentos": 0,
                    "orgaos": set()
                }

            totais[key]["valor_total"] += d.get("valor", 0)
            totais[key]["qtd_pagamentos"] += 1
            totais[key]["orgaos"].add(d.get("orgao", ""))

        # Converter sets para listas e ordenar
        for data in totais.values():
            data["orgaos"] = list(data["orgaos"])

        ranking = sorted(totais.values(), key=lambda x: x["valor_total"], reverse=True)

        # Calcular percentual
        total_geral = sum(d.get("valor", 0) for d in pagamentos)
        for item in ranking:
            if total_geral > 0:
                item["percentual"] = (item["valor_total"] / total_geral) * 100
            else:
                item["percentual"] = 0

        return ranking[:top_n]

    def get_despesas_por_orgao(self, ano: int) -> Dict[str, float]:
        """
        Agrupa despesas por órgão.

        Args:
            ano: Ano de referência

        Returns:
            Dicionário com totais por órgão
        """
        despesas = self.get_despesas_ano(ano)

        # Filtrar pagamentos
        pagamentos = [d for d in despesas if "PAGO" in d.get("evento", "").upper()]

        totais = {}
        for d in pagamentos:
            orgao = d.get("orgao", "Não informado")
            totais[orgao] = totais.get(orgao, 0) + d.get("valor", 0)

        return dict(sorted(totais.items(), key=lambda x: x[1], reverse=True))

    def get_despesas_por_funcao(self, ano: int) -> Dict[str, float]:
        """
        Agrupa despesas por função (quando disponível).

        Args:
            ano: Ano de referência

        Returns:
            Dicionário com totais por função
        """
        despesas = self.get_despesas_ano(ano)
        pagamentos = [d for d in despesas if "PAGO" in d.get("evento", "").upper()]

        totais = {}
        for d in pagamentos:
            funcao = d.get("funcao", d.get("orgao", "Outros"))
            totais[funcao] = totais.get(funcao, 0) + d.get("valor", 0)

        return dict(sorted(totais.items(), key=lambda x: x[1], reverse=True))

    def get_evolucao_mensal(self, ano: int) -> Dict[str, Dict[str, float]]:
        """
        Calcula evolução mensal de despesas.

        Args:
            ano: Ano de referência

        Returns:
            Dicionário com totais mensais por tipo de evento
        """
        meses = {i: {"empenhado": 0, "liquidado": 0, "pago": 0} for i in range(1, 13)}

        for mes in range(1, 13):
            despesas = self.get_despesas(ano, mes)

            for d in despesas:
                evento = d.get("evento", "").upper()
                valor = d.get("valor", 0)

                if "EMPENH" in evento:
                    meses[mes]["empenhado"] += valor
                elif "LIQUID" in evento:
                    meses[mes]["liquidado"] += valor
                elif "PAG" in evento:
                    meses[mes]["pago"] += valor

        return meses

    def detect_concentracao_fornecedor(
        self,
        ano: int,
        limite_percentual: float = 10.0
    ) -> List[Dict[str, Any]]:
        """
        Detecta fornecedores com alta concentração de pagamentos.

        Concentração excessiva pode indicar direcionamento ou
        falta de competitividade nas licitações.

        Args:
            ano: Ano de referência
            limite_percentual: Percentual acima do qual gera alerta

        Returns:
            Lista de alertas de concentração
        """
        fornecedores = self.get_maiores_fornecedores(ano, top_n=50)
        alertas = []

        for f in fornecedores:
            if f["percentual"] > limite_percentual:
                alertas.append({
                    "tipo": "alerta",
                    "categoria": "concentracao",
                    "titulo": f"Alta concentração: {f['fornecedor'][:30]}",
                    "descricao": (
                        f"Fornecedor recebeu {f['percentual']:.1f}% do total de pagamentos "
                        f"(R$ {f['valor_total']/1_000_000:.2f} milhões)"
                    ),
                    "fornecedor": f["fornecedor"],
                    "cnpj_parcial": f["cnpj_parcial"],
                    "valor": f["valor_total"],
                    "percentual": f["percentual"],
                    "data": datetime.now().strftime("%Y-%m-%d")
                })

        return alertas

    def _parse_valor(self, valor: Any) -> float:
        """Converte valor para float."""
        if isinstance(valor, (int, float)):
            return float(valor)
        if isinstance(valor, str):
            valor = valor.replace("R$", "").replace(".", "").replace(",", ".").strip()
            try:
                return float(valor)
            except ValueError:
                return 0.0
        return 0.0

    def get_dados_para_dashboard(self, ano: int = None) -> Dict[str, Any]:
        """
        Retorna dados formatados para o dashboard.

        Args:
            ano: Ano de referência

        Returns:
            Dicionário com dados para o dashboard
        """
        if ano is None:
            ano = datetime.now().year

        logger.info(f"Gerando dados TCE-SP para dashboard - {ano}")

        # Coletar dados (apenas últimos 3 meses para não sobrecarregar)
        mes_atual = datetime.now().month
        meses_recentes = []
        for m in range(max(1, mes_atual - 2), mes_atual + 1):
            despesas = self.get_despesas(ano, m)
            meses_recentes.extend(despesas)

        # Maiores fornecedores
        fornecedores = self.get_maiores_fornecedores(ano, top_n=10)

        # Alertas de concentração
        alertas = self.detect_concentracao_fornecedor(ano)

        # Totais
        total_empenhado = sum(
            d["valor"] for d in meses_recentes
            if "EMPENH" in d.get("evento", "").upper()
        )
        total_pago = sum(
            d["valor"] for d in meses_recentes
            if "PAG" in d.get("evento", "").upper()
        )

        return {
            "fonte": "TCE-SP",
            "ano": ano,
            "ultima_atualizacao": datetime.now().isoformat(),
            "periodo": f"Últimos 3 meses de {ano}",
            "totais": {
                "empenhado": total_empenhado,
                "pago": total_pago,
                "empenhado_fmt": f"R$ {total_empenhado/1_000_000:.1f}M",
                "pago_fmt": f"R$ {total_pago/1_000_000:.1f}M"
            },
            "fornecedores": fornecedores[:5],
            "alertas_concentracao": alertas,
            "qtd_despesas": len(meses_recentes)
        }
