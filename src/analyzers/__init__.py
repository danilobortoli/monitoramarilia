"""
Módulos de análise de dados e detecção de anomalias.

Analisadores disponíveis:
- AnomalyDetector: Detecta anomalias em despesas, contratos e licitações
"""

from .anomaly_detector import AnomalyDetector

__all__ = [
    "AnomalyDetector",
]
