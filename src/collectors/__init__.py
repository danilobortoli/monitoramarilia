"""
Módulos de coleta de dados do Portal de Transparência.
"""

from .base import BaseCollector
from .licitacoes import LicitacoesCollector
from .contratos import ContratosCollector
from .despesas import DespesasCollector
from .receitas import ReceitasCollector
from .pessoal import PessoalCollector

__all__ = [
    "BaseCollector",
    "LicitacoesCollector",
    "ContratosCollector",
    "DespesasCollector",
    "ReceitasCollector",
    "PessoalCollector",
]
