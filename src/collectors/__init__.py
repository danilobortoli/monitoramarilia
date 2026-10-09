"""
Módulos de coleta de dados de fontes abertas.

Coletores disponíveis:
- SiconfiCollector: Dados fiscais do Tesouro Nacional (RGF, RREO, DCA)
- TCESPCollector: Despesas e receitas do TCE-SP
- PortalFederalCollector: Convênios, transferências e sanções federais
- PortalMariliaCollector: Portal da Transparência de Marília (SMARAPD)
- DadosAbertosMariliaCollector: Dados abertos do site da Prefeitura de Marília
"""

from .siconfi import SiconfiCollector
from .tce_sp import TCESPCollector
from .portal_federal import PortalFederalCollector
from .portal_marilia import PortalMariliaCollector
from .dados_abertos_marilia import DadosAbertosMariliaCollector

__all__ = [
    "SiconfiCollector",
    "TCESPCollector",
    "PortalFederalCollector",
    "PortalMariliaCollector",
    "DadosAbertosMariliaCollector",
]
