"""
Detector de anomalias em dados de transparência pública.
Identifica padrões suspeitos em despesas, contratos e licitações.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import statistics
import logging

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Níveis de severidade dos alertas."""
    CRITICO = "critico"
    ALERTA = "alerta"
    INFO = "info"


class AlertCategory(Enum):
    """Categorias de alertas."""
    DESPESAS = "despesas"
    CONTRATOS = "contratos"
    LICITACOES = "licitacoes"
    FORNECEDORES = "fornecedores"
    LAI = "lai"
    PESSOAL = "pessoal"


@dataclass
class Alert:
    """Representa um alerta detectado."""
    id: int
    tipo: AlertSeverity
    titulo: str
    descricao: str
    data: str
    categoria: AlertCategory
    dados_referencia: Optional[Dict] = None


class AnomalyDetector:
    """
    Detector de anomalias para controle social.
    Implementa diversos algoritmos de detecção de irregularidades.
    """

    def __init__(self):
        self.alerts: List[Alert] = []
        self.alert_counter = 0

    def _create_alert(
        self,
        tipo: AlertSeverity,
        titulo: str,
        descricao: str,
        categoria: AlertCategory,
        dados: Optional[Dict] = None
    ) -> Alert:
        """Cria um novo alerta."""
        self.alert_counter += 1
        return Alert(
            id=self.alert_counter,
            tipo=tipo,
            titulo=titulo,
            descricao=descricao,
            data=datetime.now().strftime("%Y-%m-%d"),
            categoria=categoria,
            dados_referencia=dados
        )

    def detect_outliers_zscore(
        self,
        valores: List[float],
        threshold: float = 2.0
    ) -> List[int]:
        """
        Detecta outliers usando Z-score.

        Args:
            valores: Lista de valores numéricos
            threshold: Número de desvios padrão para considerar outlier

        Returns:
            Índices dos valores outliers
        """
        if len(valores) < 3:
            return []

        media = statistics.mean(valores)
        desvio = statistics.stdev(valores)

        if desvio == 0:
            return []

        outliers = []
        for i, v in enumerate(valores):
            z_score = abs(v - media) / desvio
            if z_score > threshold:
                outliers.append(i)

        return outliers

    def detect_fracionamento(
        self,
        despesas: List[Dict],
        limite_dispensa: float = 17600.0,  # Limite de dispensa por valor
        janela_dias: int = 30
    ) -> List[Alert]:
        """
        Detecta possível fracionamento de despesas.
        Identifica múltiplas compras similares que somadas ultrapassam o limite de licitação.

        Args:
            despesas: Lista de despesas
            limite_dispensa: Valor limite para dispensa de licitação
            janela_dias: Período em dias para análise

        Returns:
            Lista de alertas de fracionamento
        """
        alerts = []

        # Agrupar por fornecedor e elemento de despesa
        grupos = {}
        for d in despesas:
            key = (
                d.get("favorecido", "").upper(),
                d.get("elemento_despesa", "")
            )
            if key not in grupos:
                grupos[key] = []
            grupos[key].append(d)

        for (fornecedor, elemento), items in grupos.items():
            if len(items) < 2:
                continue

            # Ordenar por data
            items_sorted = sorted(items, key=lambda x: x.get("data_empenho", ""))

            # Verificar compras em janela de tempo
            for i, item in enumerate(items_sorted):
                janela = []
                data_ref = item.get("data_empenho", "")

                for j, other in enumerate(items_sorted):
                    if i == j:
                        janela.append(other)
                        continue

                    # Simplificação: considerar mesmo mês como janela
                    if data_ref[:7] == other.get("data_empenho", "")[:7]:
                        janela.append(other)

                if len(janela) >= 3:
                    total = sum(d.get("valor_empenhado", 0) for d in janela)

                    if total > limite_dispensa:
                        alert = self._create_alert(
                            tipo=AlertSeverity.CRITICO,
                            titulo="Possível fracionamento de despesas",
                            descricao=(
                                f"Detectadas {len(janela)} compras de '{elemento}' "
                                f"com {fornecedor}, totalizando R$ {total:,.2f} no período. "
                                f"Valores individuais abaixo de R$ {limite_dispensa:,.2f} "
                                f"podem indicar fracionamento para evitar licitação."
                            ),
                            categoria=AlertCategory.DESPESAS,
                            dados={"fornecedor": fornecedor, "total": total, "qtd": len(janela)}
                        )
                        alerts.append(alert)
                        break  # Um alerta por grupo

        return alerts

    def detect_concentracao_fornecedor(
        self,
        despesas: List[Dict],
        limite_percentual: float = 10.0
    ) -> List[Alert]:
        """
        Detecta concentração excessiva de pagamentos em um fornecedor.

        Args:
            despesas: Lista de despesas
            limite_percentual: Percentual máximo aceitável

        Returns:
            Lista de alertas
        """
        alerts = []

        total_geral = sum(d.get("valor_pago", 0) for d in despesas)
        if total_geral == 0:
            return alerts

        # Agrupar por fornecedor
        por_fornecedor = {}
        for d in despesas:
            forn = d.get("favorecido", "Não informado")
            por_fornecedor[forn] = por_fornecedor.get(forn, 0) + d.get("valor_pago", 0)

        for fornecedor, valor in por_fornecedor.items():
            percentual = (valor / total_geral) * 100

            if percentual > limite_percentual:
                alert = self._create_alert(
                    tipo=AlertSeverity.ALERTA,
                    titulo="Fornecedor com alta concentração",
                    descricao=(
                        f"{fornecedor} recebeu {percentual:.1f}% do total de pagamentos "
                        f"(R$ {valor:,.2f} de R$ {total_geral:,.2f}). "
                        f"Concentração acima de {limite_percentual}% requer análise."
                    ),
                    categoria=AlertCategory.FORNECEDORES,
                    dados={"fornecedor": fornecedor, "valor": valor, "percentual": percentual}
                )
                alerts.append(alert)

        return alerts

    def detect_aditivos_excessivos(
        self,
        contratos: List[Dict],
        limite_percentual: float = 25.0
    ) -> List[Alert]:
        """
        Detecta contratos com aditivos acima do limite legal.

        Args:
            contratos: Lista de contratos
            limite_percentual: Limite legal (25% por padrão)

        Returns:
            Lista de alertas
        """
        alerts = []

        for c in contratos:
            valor_original = c.get("valor_original", 0)
            valor_aditivos = c.get("valor_aditivos", 0)

            if valor_original > 0:
                percentual = (valor_aditivos / valor_original) * 100

                if percentual > limite_percentual:
                    alert = self._create_alert(
                        tipo=AlertSeverity.CRITICO,
                        titulo="Aditivo contratual acima do limite legal",
                        descricao=(
                            f"Contrato {c.get('numero', 'N/I')} teve aditivo de {percentual:.1f}%, "
                            f"superando o limite de {limite_percentual}% "
                            f"(Art. 65, §1º da Lei 8.666/93). "
                            f"Valor original: R$ {valor_original:,.2f}, "
                            f"Aditivos: R$ {valor_aditivos:,.2f}."
                        ),
                        categoria=AlertCategory.CONTRATOS,
                        dados=c
                    )
                    alerts.append(alert)

        return alerts

    def detect_dispensa_valor_alto(
        self,
        contratos: List[Dict],
        limite: float = 50000.0
    ) -> List[Alert]:
        """
        Detecta contratos por dispensa com valores elevados.
        """
        alerts = []

        for c in contratos:
            modalidade = c.get("modalidade_licitacao", "").lower()
            valor = c.get("valor_atual", 0)

            if "dispensa" in modalidade and valor > limite:
                alert = self._create_alert(
                    tipo=AlertSeverity.CRITICO,
                    titulo="Contrato por dispensa com valor elevado",
                    descricao=(
                        f"Contrato {c.get('numero', 'N/I')} no valor de R$ {valor:,.2f} "
                        f"firmado por dispensa de licitação. "
                        f"Objeto: {c.get('objeto', 'N/I')}. "
                        f"Verificar enquadramento legal da dispensa."
                    ),
                    categoria=AlertCategory.CONTRATOS,
                    dados=c
                )
                alerts.append(alert)

        return alerts

    def detect_licitacao_deserta_recorrente(
        self,
        licitacoes: List[Dict],
        limite_recorrencia: int = 2
    ) -> List[Alert]:
        """
        Detecta licitações desertas recorrentes para o mesmo objeto.
        """
        alerts = []

        # Agrupar por objeto similar
        por_objeto = {}
        for lic in licitacoes:
            if lic.get("status", "").lower() in ["deserta", "fracassada"]:
                objeto = lic.get("objeto", "")[:50].lower()  # Primeiros 50 chars
                por_objeto.setdefault(objeto, []).append(lic)

        for objeto, lics in por_objeto.items():
            if len(lics) >= limite_recorrencia:
                alert = self._create_alert(
                    tipo=AlertSeverity.ALERTA,
                    titulo="Licitação deserta/fracassada recorrente",
                    descricao=(
                        f"Objeto '{objeto}...' teve {len(lics)} licitações desertas/fracassadas. "
                        f"Pode indicar especificações restritivas ou preço de referência inadequado."
                    ),
                    categoria=AlertCategory.LICITACOES,
                    dados={"objeto": objeto, "quantidade": len(lics)}
                )
                alerts.append(alert)

        return alerts

    def run_full_analysis(
        self,
        despesas: List[Dict] = None,
        contratos: List[Dict] = None,
        licitacoes: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Executa análise completa de anomalias.

        Returns:
            Relatório com todos os alertas detectados
        """
        self.alerts = []
        self.alert_counter = 0

        if despesas:
            self.alerts.extend(self.detect_fracionamento(despesas))
            self.alerts.extend(self.detect_concentracao_fornecedor(despesas))

        if contratos:
            self.alerts.extend(self.detect_aditivos_excessivos(contratos))
            self.alerts.extend(self.detect_dispensa_valor_alto(contratos))

        if licitacoes:
            self.alerts.extend(self.detect_licitacao_deserta_recorrente(licitacoes))

        return {
            "data_analise": datetime.now().isoformat(),
            "total_alertas": len(self.alerts),
            "criticos": sum(1 for a in self.alerts if a.tipo == AlertSeverity.CRITICO),
            "alertas": sum(1 for a in self.alerts if a.tipo == AlertSeverity.ALERTA),
            "info": sum(1 for a in self.alerts if a.tipo == AlertSeverity.INFO),
            "detalhes": [
                {
                    "id": a.id,
                    "tipo": a.tipo.value,
                    "titulo": a.titulo,
                    "descricao": a.descricao,
                    "data": a.data,
                    "categoria": a.categoria.value
                }
                for a in self.alerts
            ]
        }

    def get_alerts_for_dashboard(self) -> List[Dict]:
        """
        Retorna alertas formatados para o dashboard.
        """
        return [
            {
                "id": a.id,
                "tipo": a.tipo.value,
                "titulo": a.titulo,
                "descricao": a.descricao,
                "data": a.data,
                "categoria": a.categoria.value
            }
            for a in sorted(self.alerts, key=lambda x: (
                0 if x.tipo == AlertSeverity.CRITICO else
                1 if x.tipo == AlertSeverity.ALERTA else 2
            ))
        ]
