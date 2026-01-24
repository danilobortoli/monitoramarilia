"""
Modelo de Dados Integrados - MonitoraMarília

Este módulo conecta dados de múltiplas fontes:
- SICONFI (Tesouro Nacional): RGF, RREO, DCA
- TCE-SP: Despesas e receitas detalhadas
- Portal Federal: Convênios, transferências, sanções
- Portal local (SMARAPD): Licitações, contratos

Permite cruzamentos como:
- Verificar fornecedores contra listas de sanções (CEIS, CNEP)
- Comparar despesas locais com transferências federais
- Analisar limites da LRF com dados detalhados
- Identificar relações entre licitações, contratos e pagamentos
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Fornecedor:
    """Representa um fornecedor com dados consolidados."""
    cnpj: str
    nome: str
    valor_total_contratos: float = 0
    valor_total_pagamentos: float = 0
    qtd_contratos: int = 0
    qtd_pagamentos: int = 0
    situacao_ceis: Optional[str] = None  # REGULAR, SANCIONADA
    situacao_cnep: Optional[str] = None
    contratos: List[str] = field(default_factory=list)
    alertas: List[str] = field(default_factory=list)


@dataclass
class ResumoFiscal:
    """Resumo fiscal consolidado do município."""
    ano: int
    rcl: float  # Receita Corrente Líquida
    despesa_pessoal: float
    percentual_pessoal: float
    divida_consolidada: float
    percentual_divida: float
    limite_pessoal_ok: bool
    limite_divida_ok: bool
    alertas_lrf: List[Dict] = field(default_factory=list)


@dataclass
class TransferenciaFederal:
    """Transferência de recurso federal."""
    tipo: str  # constitucional, legal, voluntária
    programa: str
    valor: float
    data: str
    orgao_origem: str


class DadosIntegrados:
    """
    Classe principal para integração de dados de múltiplas fontes.

    Permite consultas cruzadas e análises consolidadas.
    """

    CODIGO_IBGE_MARILIA = "3529005"

    def __init__(self):
        """Inicializa o integrador de dados."""
        self.fornecedores: Dict[str, Fornecedor] = {}
        self.resumo_fiscal: Optional[ResumoFiscal] = None
        self.transferencias: List[TransferenciaFederal] = []
        self.alertas: List[Dict] = []
        self.ultima_atualizacao: Optional[str] = None

        # Coletores (lazy loading)
        self._siconfi = None
        self._tce_sp = None
        self._portal_federal = None

    @property
    def siconfi(self):
        """Retorna coletor SICONFI (lazy loading)."""
        if self._siconfi is None:
            from collectors.siconfi import SiconfiCollector
            self._siconfi = SiconfiCollector()
        return self._siconfi

    @property
    def tce_sp(self):
        """Retorna coletor TCE-SP (lazy loading)."""
        if self._tce_sp is None:
            from collectors.tce_sp import TCESPCollector
            self._tce_sp = TCESPCollector()
        return self._tce_sp

    @property
    def portal_federal(self):
        """Retorna coletor Portal Federal (lazy loading)."""
        if self._portal_federal is None:
            from collectors.portal_federal import PortalFederalCollector
            self._portal_federal = PortalFederalCollector()
        return self._portal_federal

    def carregar_dados_fiscais(self, ano: int) -> ResumoFiscal:
        """
        Carrega dados fiscais do SICONFI.

        Args:
            ano: Ano de referência

        Returns:
            Resumo fiscal do município
        """
        logger.info(f"Carregando dados fiscais SICONFI - {ano}")

        # Buscar RCL
        rcl = self.siconfi.get_receita_corrente_liquida(ano) or 0

        # Buscar dados de pessoal
        pessoal_data = self.siconfi.get_despesa_pessoal(ano)
        despesa_pessoal = 0
        percentual_pessoal = 0

        for ind in pessoal_data.get("indicadores", []):
            if "TOTAL" in ind.get("conta", "").upper():
                if "%" in ind.get("coluna", ""):
                    percentual_pessoal = ind.get("valor", 0)
                else:
                    despesa_pessoal = ind.get("valor", 0)

        # Buscar dados de dívida
        divida_data = self.siconfi.get_divida_consolidada(ano)
        divida_consolidada = 0
        for item in divida_data.get("divida", []):
            if "TOTAL" in item.get("conta", "").upper():
                divida_consolidada = item.get("valor", 0)
                break

        percentual_divida = (divida_consolidada / rcl * 100) if rcl > 0 else 0

        # Alertas LRF
        alertas = self.siconfi.verificar_alertas_lrf(ano)

        self.resumo_fiscal = ResumoFiscal(
            ano=ano,
            rcl=rcl,
            despesa_pessoal=despesa_pessoal,
            percentual_pessoal=percentual_pessoal,
            divida_consolidada=divida_consolidada,
            percentual_divida=percentual_divida,
            limite_pessoal_ok=percentual_pessoal <= 54,
            limite_divida_ok=percentual_divida <= 120,
            alertas_lrf=alertas
        )

        return self.resumo_fiscal

    def carregar_fornecedores_tce(self, ano: int) -> Dict[str, Fornecedor]:
        """
        Carrega fornecedores a partir dos dados do TCE-SP.

        Args:
            ano: Ano de referência

        Returns:
            Dicionário de fornecedores indexados por CNPJ
        """
        logger.info(f"Carregando fornecedores TCE-SP - {ano}")

        maiores = self.tce_sp.get_maiores_fornecedores(ano, top_n=100)

        for f in maiores:
            cnpj = f.get("cnpj_parcial", "")
            if not cnpj:
                continue

            if cnpj not in self.fornecedores:
                self.fornecedores[cnpj] = Fornecedor(
                    cnpj=cnpj,
                    nome=f.get("fornecedor", ""),
                )

            forn = self.fornecedores[cnpj]
            forn.valor_total_pagamentos = f.get("valor_total", 0)
            forn.qtd_pagamentos = f.get("qtd_pagamentos", 0)

        return self.fornecedores

    def verificar_fornecedores_sancoes(self, cnpjs: List[str] = None) -> List[Dict]:
        """
        Verifica fornecedores contra listas de sanções federais.

        Args:
            cnpjs: Lista de CNPJs a verificar (ou todos carregados)

        Returns:
            Lista de fornecedores com sanções encontradas
        """
        if not self.portal_federal.api_key:
            logger.warning("API Key do Portal Federal não configurada")
            return []

        cnpjs_verificar = cnpjs or list(self.fornecedores.keys())
        sancionados = []

        for cnpj in cnpjs_verificar:
            resultado = self.portal_federal.verificar_fornecedor_completo(cnpj)

            if resultado.get("situacao") == "IRREGULAR":
                # Atualizar fornecedor se existir
                if cnpj in self.fornecedores:
                    forn = self.fornecedores[cnpj]
                    for sancao in resultado.get("sancoes", []):
                        forn.alertas.append(
                            f"Sancionado no {sancao.get('cadastro')}"
                        )
                        if sancao.get("cadastro") == "CEIS":
                            forn.situacao_ceis = "SANCIONADA"
                        elif sancao.get("cadastro") == "CNEP":
                            forn.situacao_cnep = "PUNIDA"

                sancionados.append({
                    "cnpj": cnpj,
                    "nome": self.fornecedores.get(cnpj, Fornecedor(cnpj, "")).nome,
                    "sancoes": resultado.get("sancoes", []),
                    "tipo": "critico",
                    "titulo": "Fornecedor com sanção federal",
                    "descricao": f"Fornecedor {cnpj} encontrado em cadastro de sanções"
                })

        self.alertas.extend(sancionados)
        return sancionados

    def carregar_transferencias_federais(self, ano: int) -> List[TransferenciaFederal]:
        """
        Carrega transferências federais para o município.

        Args:
            ano: Ano de referência

        Returns:
            Lista de transferências
        """
        logger.info(f"Carregando transferências federais - {ano}")

        if not self.portal_federal.api_key:
            logger.warning("API Key do Portal Federal não configurada")
            return []

        dados = self.portal_federal.get_transferencias(ano)

        self.transferencias = [
            TransferenciaFederal(
                tipo=t.get("tipo", ""),
                programa=t.get("programa", ""),
                valor=t.get("valor", 0),
                data=t.get("data", ""),
                orgao_origem=t.get("orgao", "")
            )
            for t in dados
        ]

        return self.transferencias

    def gerar_relatorio_integrado(self, ano: int) -> Dict[str, Any]:
        """
        Gera relatório consolidado com dados de todas as fontes.

        Args:
            ano: Ano de referência

        Returns:
            Relatório integrado
        """
        logger.info(f"Gerando relatório integrado - {ano}")

        # Carregar dados de cada fonte
        self.carregar_dados_fiscais(ano)
        self.carregar_fornecedores_tce(ano)

        # Totais de transferências (se API disponível)
        total_transferencias = 0
        transferencias_por_tipo = {}
        if self.portal_federal.api_key:
            self.carregar_transferencias_federais(ano)
            total_transferencias = sum(t.valor for t in self.transferencias)
            for t in self.transferencias:
                transferencias_por_tipo[t.tipo] = (
                    transferencias_por_tipo.get(t.tipo, 0) + t.valor
                )

        # Top fornecedores
        top_fornecedores = sorted(
            self.fornecedores.values(),
            key=lambda x: x.valor_total_pagamentos,
            reverse=True
        )[:10]

        self.ultima_atualizacao = datetime.now().isoformat()

        return {
            "municipio": "Marília",
            "codigo_ibge": self.CODIGO_IBGE_MARILIA,
            "ano": ano,
            "ultima_atualizacao": self.ultima_atualizacao,

            # Dados fiscais (SICONFI)
            "fiscal": {
                "fonte": "SICONFI - Tesouro Nacional",
                "rcl": self.resumo_fiscal.rcl if self.resumo_fiscal else 0,
                "rcl_fmt": f"R$ {(self.resumo_fiscal.rcl or 0)/1_000_000:.1f}M",
                "despesa_pessoal": {
                    "valor": self.resumo_fiscal.despesa_pessoal if self.resumo_fiscal else 0,
                    "percentual": self.resumo_fiscal.percentual_pessoal if self.resumo_fiscal else 0,
                    "limite": 54,
                    "status": "ok" if (self.resumo_fiscal and self.resumo_fiscal.limite_pessoal_ok) else "critico"
                },
                "divida": {
                    "valor": self.resumo_fiscal.divida_consolidada if self.resumo_fiscal else 0,
                    "percentual": self.resumo_fiscal.percentual_divida if self.resumo_fiscal else 0,
                    "limite": 120,
                    "status": "ok" if (self.resumo_fiscal and self.resumo_fiscal.limite_divida_ok) else "critico"
                }
            },

            # Fornecedores (TCE-SP)
            "fornecedores": {
                "fonte": "TCE-SP",
                "total_analisados": len(self.fornecedores),
                "top_10": [
                    {
                        "cnpj": f.cnpj,
                        "nome": f.nome,
                        "valor": f.valor_total_pagamentos,
                        "valor_fmt": f"R$ {f.valor_total_pagamentos/1_000_000:.2f}M",
                        "qtd_pagamentos": f.qtd_pagamentos,
                        "situacao_sancoes": "REGULAR" if not f.alertas else "ALERTA"
                    }
                    for f in top_fornecedores
                ]
            },

            # Transferências federais
            "transferencias_federais": {
                "fonte": "Portal Transparência Federal",
                "disponivel": bool(self.portal_federal.api_key),
                "total": total_transferencias,
                "total_fmt": f"R$ {total_transferencias/1_000_000:.2f}M",
                "por_tipo": transferencias_por_tipo
            },

            # Alertas consolidados
            "alertas": {
                "total": len(self.alertas) + len(self.resumo_fiscal.alertas_lrf if self.resumo_fiscal else []),
                "lrf": self.resumo_fiscal.alertas_lrf if self.resumo_fiscal else [],
                "fornecedores": [a for a in self.alertas if "Fornecedor" in a.get("titulo", "")],
                "outros": [a for a in self.alertas if "Fornecedor" not in a.get("titulo", "")]
            },

            # Metadados das fontes
            "fontes": {
                "siconfi": {
                    "nome": "SICONFI - Tesouro Nacional",
                    "url": "https://siconfi.tesouro.gov.br",
                    "dados": ["RGF", "RREO", "DCA"]
                },
                "tce_sp": {
                    "nome": "TCE-SP - Tribunal de Contas SP",
                    "url": "https://transparencia.tce.sp.gov.br",
                    "dados": ["Despesas", "Receitas"]
                },
                "portal_federal": {
                    "nome": "Portal da Transparência Federal",
                    "url": "https://portaldatransparencia.gov.br",
                    "dados": ["Convênios", "Transferências", "CEIS", "CNEP"],
                    "requer_api_key": True
                }
            }
        }

    def exportar_para_dashboard(self, ano: int = None) -> Dict[str, Any]:
        """
        Exporta dados no formato esperado pelo dashboard.

        Args:
            ano: Ano de referência

        Returns:
            Dados formatados para o dashboard
        """
        if ano is None:
            ano = datetime.now().year

        relatorio = self.gerar_relatorio_integrado(ano)

        # Formatar para o dashboard
        return {
            "lastUpdate": relatorio["ultima_atualizacao"],
            "ano": ano,
            "portal": "https://transparencia.marilia.sp.gov.br",

            "kpis": {
                "rclValor": relatorio["fiscal"]["rcl_fmt"],
                "pessoalPercentual": f"{relatorio['fiscal']['despesa_pessoal']['percentual']:.1f}%",
                "pessoalStatus": relatorio["fiscal"]["despesa_pessoal"]["status"],
                "dividaPercentual": f"{relatorio['fiscal']['divida']['percentual']:.1f}%",
                "dividaStatus": relatorio["fiscal"]["divida"]["status"],
                "transferenciasValor": relatorio["transferencias_federais"]["total_fmt"],
                "alertasCount": relatorio["alertas"]["total"],
                "fornecedoresAnalisados": relatorio["fornecedores"]["total_analisados"]
            },

            "fiscal": relatorio["fiscal"],
            "fornecedores": relatorio["fornecedores"]["top_10"],
            "transferencias": relatorio["transferencias_federais"],
            "alertas": relatorio["alertas"],
            "fontes": relatorio["fontes"]
        }
