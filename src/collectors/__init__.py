"""
Módulos de coleta de dados de fontes abertas.

Coletores disponíveis:
- SiconfiCollector: Dados fiscais do Tesouro Nacional (RGF, RREO, DCA)
- TCESPCollector: Despesas e receitas do TCE-SP
- PortalFederalCollector: Convênios, transferências e sanções federais
"""

from .siconfi import SiconfiCollector
from .tce_sp import TCESPCollector
from .portal_federal import PortalFederalCollector

__all__ = [
    "SiconfiCollector",
    "TCESPCollector",
    "PortalFederalCollector",
]
