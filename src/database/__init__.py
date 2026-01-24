"""
Módulo de banco de dados SQLite para armazenamento histórico.

Armazena dados coletados das APIs para:
- Análise histórica e tendências
- Geração de relatórios
- Comparação entre períodos
"""

from .models import DatabaseManager, init_database, get_connection

__all__ = [
    "DatabaseManager",
    "init_database",
    "get_connection",
]
