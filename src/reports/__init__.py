"""
Modulo de geracao de relatorios PDF para o MonitoraMarilia.

Utiliza WeasyPrint para converter HTML em PDF com formatacao profissional.
"""

from .generator import (
    ReportGenerator,
    FiscalReport,
    SupplierReport,
    TransferReport,
    ConsolidatedReport,
)

__all__ = [
    "ReportGenerator",
    "FiscalReport",
    "SupplierReport",
    "TransferReport",
    "ConsolidatedReport",
]
