"""
Gerador de Relatorios PDF para o MonitoraMarilia.

Gera relatorios de transparencia fiscal em PDF utilizando WeasyPrint.
Inclui relatorios fiscais (SICONFI), de fornecedores (TCE-SP),
transferencias federais e consolidados mensais/anuais.

Autor: MATRA - Movimento por uma Administracao Transparente de Marilia
"""

import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

logger = logging.getLogger(__name__)

# Diretorio padrao para salvar relatorios
REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"


def format_currency(value: Union[float, int, None], compact: bool = False) -> str:
    """
    Formata valor monetario no padrao brasileiro.

    Args:
        value: Valor numerico
        compact: Se True, usa formato compacto (milhoes/bilhoes)

    Returns:
        String formatada (ex: R$ 1.234.567,89)
    """
    if value is None:
        return "N/D"

    try:
        value = float(value)
    except (ValueError, TypeError):
        return "N/D"

    if compact:
        if abs(value) >= 1_000_000_000:
            return f"R$ {value/1_000_000_000:,.2f}B".replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(value) >= 1_000_000:
            return f"R$ {value/1_000_000:,.2f}M".replace(",", "X").replace(".", ",").replace("X", ".")
        elif abs(value) >= 1_000:
            return f"R$ {value/1_000:,.2f}K".replace(",", "X").replace(".", ",").replace("X", ".")

    # Formato completo
    formatted = f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted


def format_percentage(value: Union[float, int, None], decimals: int = 1) -> str:
    """
    Formata percentual no padrao brasileiro.

    Args:
        value: Valor numerico (ja em percentual, nao decimal)
        decimals: Casas decimais

    Returns:
        String formatada (ex: 54,3%)
    """
    if value is None:
        return "N/D"

    try:
        value = float(value)
        formatted = f"{value:.{decimals}f}%".replace(".", ",")
        return formatted
    except (ValueError, TypeError):
        return "N/D"


def format_date(date_str: Optional[str], output_format: str = "%d/%m/%Y") -> str:
    """
    Formata data para o padrao brasileiro.

    Args:
        date_str: Data em formato ISO ou similar
        output_format: Formato de saida

    Returns:
        Data formatada
    """
    if not date_str:
        return "N/D"

    # Tentar varios formatos de entrada
    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d/%m/%Y",
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str[:19] if len(date_str) > 19 else date_str, fmt)
            return dt.strftime(output_format)
        except ValueError:
            continue

    return date_str


# ============================================================================
# CSS Base para todos os relatorios
# ============================================================================

BASE_CSS = """
@page {
    size: A4;
    margin: 2cm 1.5cm;
    @top-center {
        content: "MonitoraMarilia - MATRA";
        font-size: 9pt;
        color: #666;
    }
    @bottom-center {
        content: "Pagina " counter(page) " de " counter(pages);
        font-size: 9pt;
        color: #666;
    }
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: 'Helvetica Neue', Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.4;
    color: #333;
}

/* Header / Cabecalho */
.header {
    text-align: center;
    padding-bottom: 20px;
    border-bottom: 3px solid #1a5276;
    margin-bottom: 25px;
}

.logo-placeholder {
    width: 120px;
    height: 60px;
    margin: 0 auto 15px;
    background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 14pt;
    letter-spacing: 2px;
}

.header h1 {
    color: #1a5276;
    font-size: 18pt;
    font-weight: 700;
    margin-bottom: 5px;
}

.header .subtitle {
    color: #666;
    font-size: 12pt;
    font-weight: normal;
}

.header .report-date {
    color: #888;
    font-size: 10pt;
    margin-top: 10px;
}

/* Titulos de secao */
h2 {
    color: #1a5276;
    font-size: 14pt;
    border-bottom: 2px solid #3498db;
    padding-bottom: 5px;
    margin: 25px 0 15px;
}

h3 {
    color: #2c3e50;
    font-size: 12pt;
    margin: 20px 0 10px;
}

/* Tabelas */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    font-size: 10pt;
}

th {
    background: #1a5276;
    color: white;
    padding: 10px 8px;
    text-align: left;
    font-weight: 600;
}

td {
    padding: 8px;
    border-bottom: 1px solid #ddd;
}

tr:nth-child(even) {
    background: #f8f9fa;
}

tr:hover {
    background: #e8f4f8;
}

.text-right {
    text-align: right;
}

.text-center {
    text-align: center;
}

/* Valores monetarios */
.currency {
    text-align: right;
    font-family: 'Courier New', monospace;
    white-space: nowrap;
}

.percentage {
    text-align: center;
    font-weight: 600;
}

/* Cards de KPI */
.kpi-container {
    display: flex;
    flex-wrap: wrap;
    gap: 15px;
    margin: 20px 0;
}

.kpi-card {
    flex: 1;
    min-width: 150px;
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-radius: 8px;
    padding: 15px;
    border-left: 4px solid #3498db;
}

.kpi-card.success {
    border-left-color: #27ae60;
}

.kpi-card.warning {
    border-left-color: #f39c12;
}

.kpi-card.danger {
    border-left-color: #e74c3c;
}

.kpi-label {
    font-size: 9pt;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.kpi-value {
    font-size: 16pt;
    font-weight: 700;
    color: #2c3e50;
    margin-top: 5px;
}

.kpi-detail {
    font-size: 9pt;
    color: #888;
    margin-top: 3px;
}

/* Alertas */
.alert {
    padding: 12px 15px;
    border-radius: 5px;
    margin: 10px 0;
    font-size: 10pt;
}

.alert-critico, .alert-danger {
    background: #fdecea;
    border-left: 4px solid #e74c3c;
    color: #c0392b;
}

.alert-alerta, .alert-warning {
    background: #fef9e7;
    border-left: 4px solid #f39c12;
    color: #b7950b;
}

.alert-info {
    background: #e8f6f3;
    border-left: 4px solid #1abc9c;
    color: #148f77;
}

.alert-title {
    font-weight: 600;
    margin-bottom: 3px;
}

/* Placeholder para graficos */
.chart-placeholder {
    background: #f8f9fa;
    border: 2px dashed #ccc;
    border-radius: 8px;
    padding: 40px;
    text-align: center;
    margin: 20px 0;
    color: #888;
}

.chart-placeholder .icon {
    font-size: 40pt;
    margin-bottom: 10px;
    opacity: 0.5;
}

/* Rodape */
.footer {
    margin-top: 40px;
    padding-top: 15px;
    border-top: 1px solid #ddd;
    font-size: 9pt;
    color: #666;
}

.footer .sources {
    margin-bottom: 10px;
}

.footer .disclaimer {
    font-style: italic;
    color: #888;
}

/* Quebra de pagina */
.page-break {
    page-break-after: always;
}

/* Status badges */
.badge {
    display: inline-block;
    padding: 3px 8px;
    border-radius: 12px;
    font-size: 9pt;
    font-weight: 600;
}

.badge-ok {
    background: #d4edda;
    color: #155724;
}

.badge-warning {
    background: #fff3cd;
    color: #856404;
}

.badge-danger {
    background: #f8d7da;
    color: #721c24;
}

/* Sumario executivo */
.executive-summary {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
}

.executive-summary h3 {
    margin-top: 0;
}

.executive-summary ul {
    margin: 10px 0 0 20px;
}

.executive-summary li {
    margin: 5px 0;
}

/* Meta info box */
.meta-info {
    background: #f5f5f5;
    padding: 15px;
    border-radius: 5px;
    margin-bottom: 20px;
}

.meta-info p {
    margin: 5px 0;
}
"""


# ============================================================================
# Classe base para relatorios
# ============================================================================

class BaseReport(ABC):
    """Classe base abstrata para todos os relatorios."""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Inicializa o gerador de relatorio.

        Args:
            output_dir: Diretorio de saida para os PDFs
        """
        self.output_dir = output_dir or REPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.css = CSS(string=BASE_CSS) if WEASYPRINT_AVAILABLE else None

    @abstractmethod
    def _build_html(self, data: Dict[str, Any]) -> str:
        """
        Constroi o HTML do relatorio.

        Args:
            data: Dados para o relatorio

        Returns:
            HTML completo como string
        """
        pass

    @abstractmethod
    def get_report_title(self) -> str:
        """Retorna o titulo do relatorio."""
        pass

    def _build_header(self, title: str, subtitle: str = "", date: str = None) -> str:
        """
        Constroi o cabecalho do relatorio.

        Args:
            title: Titulo principal
            subtitle: Subtitulo
            date: Data do relatorio

        Returns:
            HTML do cabecalho
        """
        if date is None:
            date = datetime.now().strftime("%d/%m/%Y as %H:%M")

        return f"""
        <div class="header">
            <div class="logo-placeholder">MATRA</div>
            <h1>{title}</h1>
            <div class="subtitle">{subtitle}</div>
            <div class="report-date">Gerado em: {date}</div>
        </div>
        """

    def _build_footer(self, sources: List[str] = None) -> str:
        """
        Constroi o rodape do relatorio.

        Args:
            sources: Lista de fontes de dados

        Returns:
            HTML do rodape
        """
        sources = sources or []
        sources_html = "<br>".join(sources) if sources else "APIs publicas oficiais"

        return f"""
        <div class="footer">
            <div class="sources">
                <strong>Fontes:</strong><br>
                {sources_html}
            </div>
            <div class="disclaimer">
                Este relatorio foi gerado automaticamente pelo sistema MonitoraMarilia,
                uma iniciativa do MATRA (Movimento por uma Administracao Transparente de Marilia).
                Os dados sao obtidos de fontes oficiais e podem apresentar defasagem em relacao
                aos valores mais recentes.
            </div>
        </div>
        """

    def _build_kpi_cards(self, kpis: List[Dict[str, Any]]) -> str:
        """
        Constroi cards de KPI.

        Args:
            kpis: Lista de KPIs com keys: label, value, detail, status

        Returns:
            HTML dos cards
        """
        cards = []
        for kpi in kpis:
            status_class = kpi.get("status", "")
            cards.append(f"""
            <div class="kpi-card {status_class}">
                <div class="kpi-label">{kpi.get('label', '')}</div>
                <div class="kpi-value">{kpi.get('value', 'N/D')}</div>
                <div class="kpi-detail">{kpi.get('detail', '')}</div>
            </div>
            """)

        return f'<div class="kpi-container">{"".join(cards)}</div>'

    def _build_table(
        self,
        headers: List[str],
        rows: List[List[str]],
        col_classes: List[str] = None
    ) -> str:
        """
        Constroi uma tabela HTML.

        Args:
            headers: Cabecalhos das colunas
            rows: Linhas de dados
            col_classes: Classes CSS para cada coluna

        Returns:
            HTML da tabela
        """
        col_classes = col_classes or [""] * len(headers)

        header_html = "".join(f"<th>{h}</th>" for h in headers)

        rows_html = []
        for row in rows:
            cells = []
            for i, cell in enumerate(row):
                cls = col_classes[i] if i < len(col_classes) else ""
                cells.append(f'<td class="{cls}">{cell}</td>')
            rows_html.append(f"<tr>{''.join(cells)}</tr>")

        return f"""
        <table>
            <thead><tr>{header_html}</tr></thead>
            <tbody>{''.join(rows_html)}</tbody>
        </table>
        """

    def _build_alerts_section(self, alerts: List[Dict[str, Any]]) -> str:
        """
        Constroi secao de alertas.

        Args:
            alerts: Lista de alertas

        Returns:
            HTML da secao de alertas
        """
        if not alerts:
            return '<div class="alert alert-info">Nenhum alerta identificado no periodo.</div>'

        alerts_html = []
        for alert in alerts:
            tipo = alert.get("tipo", "info").lower()
            alerts_html.append(f"""
            <div class="alert alert-{tipo}">
                <div class="alert-title">{alert.get('titulo', 'Alerta')}</div>
                <div>{alert.get('descricao', '')}</div>
            </div>
            """)

        return "".join(alerts_html)

    def _build_chart_placeholder(self, title: str, description: str = "") -> str:
        """
        Constroi placeholder para grafico.

        Args:
            title: Titulo do grafico
            description: Descricao

        Returns:
            HTML do placeholder
        """
        return f"""
        <div class="chart-placeholder">
            <div class="icon">[Grafico]</div>
            <div><strong>{title}</strong></div>
            <div>{description}</div>
        </div>
        """

    def generate(
        self,
        data: Dict[str, Any],
        filename: Optional[str] = None
    ) -> Path:
        """
        Gera o relatorio em PDF.

        Args:
            data: Dados para o relatorio
            filename: Nome do arquivo (sem extensao)

        Returns:
            Caminho do arquivo gerado
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.__class__.__name__}_{timestamp}"

        html_content = self._build_html(data)

        if not WEASYPRINT_AVAILABLE:
            logger.warning("WeasyPrint nao disponivel. Salvando apenas HTML.")
            html_path = self.output_dir / f"{filename}.html"
            html_path.write_text(html_content, encoding="utf-8")
            return html_path

        try:
            filepath = self.output_dir / f"{filename}.pdf"
            logger.info(f"Gerando relatorio: {filepath}")
            html_doc = HTML(string=html_content)
            html_doc.write_pdf(filepath, stylesheets=[self.css])
            logger.info(f"Relatorio gerado: {filepath} ({filepath.stat().st_size} bytes)")
            return filepath
        except Exception as e:
            logger.error(f"Erro ao gerar PDF: {e}")
            # Fallback para HTML
            html_path = self.output_dir / f"{filename}.html"
            html_path.write_text(html_content, encoding="utf-8")
            return html_path


# Alias para compatibilidade
class ReportGenerator(BaseReport):
    """Alias para BaseReport para compatibilidade."""

    def _build_html(self, data: Dict[str, Any]) -> str:
        return ""

    def get_report_title(self) -> str:
        return "Relatorio"


class FiscalReport(ReportGenerator):
    """Relatório de indicadores fiscais (SICONFI)."""

    def generate(self, dados: Dict[str, Any], ano: int = None) -> Optional[Path]:
        """
        Gera relatório de indicadores fiscais.

        Args:
            dados: Dados fiscais do SICONFI
            ano: Ano de referência

        Returns:
            Caminho do arquivo gerado
        """
        ano = ano or datetime.now().year

        # Extrair dados
        rcl = dados.get("rcl", 0)
        pessoal = dados.get("despesaPessoal", {})
        divida = dados.get("divida", {})
        alertas = dados.get("alertasLRF", [])

        # Status com cores
        def get_status_class(status):
            if status == "ok":
                return "status-ok"
            elif status in ["alerta", "prudencial"]:
                return "status-alerta"
            else:
                return "status-critico"

        # Gerar conteúdo
        conteudo = f"""
        <h2>Receita Corrente Líquida (RCL)</h2>
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="value">{format_currency(rcl)}</div>
                <div class="label">RCL Anual</div>
            </div>
            <div class="kpi-card">
                <div class="value">{format_currency(rcl/12)}</div>
                <div class="label">RCL Média Mensal</div>
            </div>
        </div>

        <h2>Limites da Lei de Responsabilidade Fiscal</h2>
        <table>
            <thead>
                <tr>
                    <th>Indicador</th>
                    <th>Valor</th>
                    <th>% da RCL</th>
                    <th>Limite</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Despesa com Pessoal (Executivo)</td>
                    <td>{format_currency(pessoal.get('valor', 0))}</td>
                    <td>{format_percentage(pessoal.get('percentual', 0))}</td>
                    <td>54% (máx) / 51,3% (prud) / 48,6% (alerta)</td>
                    <td class="{get_status_class(pessoal.get('status', ''))}">{pessoal.get('status', 'N/D').upper()}</td>
                </tr>
                <tr>
                    <td>Dívida Consolidada Líquida</td>
                    <td>{format_currency(divida.get('valor', 0))}</td>
                    <td>{format_percentage(divida.get('percentual', 0))}</td>
                    <td>120% (máx)</td>
                    <td class="{get_status_class(divida.get('status', ''))}">{divida.get('status', 'N/D').upper()}</td>
                </tr>
            </tbody>
        </table>

        <h2>Alertas LRF</h2>
        """

        if alertas:
            for alerta in alertas:
                alert_class = "alert-danger" if alerta.get("tipo") == "critico" else "alert-warning"
                conteudo += f"""
                <div class="alert-box {alert_class}">
                    <strong>{alerta.get('titulo', 'Alerta')}</strong><br>
                    {alerta.get('descricao', '')}
                </div>
                """
        else:
            conteudo += """
            <div class="alert-box alert-info">
                <strong>Situação Regular</strong><br>
                Não foram identificados alertas nos indicadores fiscais.
            </div>
            """

        # Renderizar e gerar PDF
        html = self._render_template(
            titulo="Relatório de Indicadores Fiscais",
            subtitulo=f"Lei de Responsabilidade Fiscal - {ano}",
            periodo=f"Ano {ano}",
            conteudo=conteudo,
            fontes=["SICONFI - Sistema de Informações Contábeis e Fiscais (Tesouro Nacional)"]
        )

        filename = f"fiscal-{ano}-{datetime.now().strftime('%Y%m%d')}.pdf"
        return self._generate_pdf(html, filename)


class SupplierReport(ReportGenerator):
    """Relatório de fornecedores (TCE-SP)."""

    def generate(self, dados: Dict[str, Any], ano: int = None) -> Optional[Path]:
        """
        Gera relatório de fornecedores.

        Args:
            dados: Dados de fornecedores do TCE-SP
            ano: Ano de referência

        Returns:
            Caminho do arquivo gerado
        """
        ano = ano or datetime.now().year

        fornecedores = dados.get("top10", dados.get("fornecedores", []))
        totais = dados.get("totais", {})
        alertas = dados.get("alertas_concentracao", [])

        # Gerar tabela de fornecedores
        conteudo = f"""
        <h2>Resumo de Execução Orçamentária</h2>
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="value">{format_currency(totais.get('empenhado', 0))}</div>
                <div class="label">Total Empenhado</div>
            </div>
            <div class="kpi-card">
                <div class="value">{format_currency(totais.get('pago', 0))}</div>
                <div class="label">Total Pago</div>
            </div>
        </div>

        <h2>Maiores Fornecedores</h2>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Fornecedor</th>
                    <th>CNPJ</th>
                    <th>Valor Total</th>
                    <th>% do Total</th>
                    <th>Pagamentos</th>
                </tr>
            </thead>
            <tbody>
        """

        for i, f in enumerate(fornecedores[:10], 1):
            conteudo += f"""
                <tr>
                    <td>{i}</td>
                    <td>{f.get('fornecedor', f.get('nome', 'N/D'))[:40]}</td>
                    <td>{f.get('cnpj_parcial', f.get('cnpj', 'N/D'))}</td>
                    <td>{format_currency(f.get('valor_total', f.get('valor', 0)))}</td>
                    <td>{format_percentage(f.get('percentual', 0))}</td>
                    <td>{f.get('qtd_pagamentos', f.get('qtdPagamentos', 0))}</td>
                </tr>
            """

        conteudo += """
            </tbody>
        </table>

        <h2>Alertas de Concentração</h2>
        """

        if alertas:
            for alerta in alertas:
                conteudo += f"""
                <div class="alert-box alert-warning">
                    <strong>{alerta.get('titulo', 'Concentração')}</strong><br>
                    {alerta.get('descricao', '')}
                </div>
                """
        else:
            conteudo += """
            <div class="alert-box alert-info">
                <strong>Distribuição Adequada</strong><br>
                Não foram identificadas concentrações excessivas de pagamentos.
            </div>
            """

        # Renderizar e gerar PDF
        html = self._render_template(
            titulo="Relatório de Fornecedores",
            subtitulo=f"Análise de Pagamentos - {ano}",
            periodo=f"Ano {ano}",
            conteudo=conteudo,
            fontes=["TCE-SP - Tribunal de Contas do Estado de São Paulo"]
        )

        filename = f"fornecedores-{ano}-{datetime.now().strftime('%Y%m%d')}.pdf"
        return self._generate_pdf(html, filename)


class TransferReport(ReportGenerator):
    """Relatório de transferências federais."""

    def generate(self, dados: Dict[str, Any], ano: int = None) -> Optional[Path]:
        """
        Gera relatório de transferências federais.

        Args:
            dados: Dados de transferências do Portal Federal
            ano: Ano de referência

        Returns:
            Caminho do arquivo gerado
        """
        ano = ano or datetime.now().year

        transferencias = dados.get("transferencias", {})
        convenios = dados.get("convenios", {})
        emendas = dados.get("emendas", {})

        conteudo = f"""
        <h2>Transferências Federais Recebidas</h2>
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="value">{format_currency(transferencias.get('total', 0))}</div>
                <div class="label">Total de Transferências</div>
            </div>
            <div class="kpi-card">
                <div class="value">{convenios.get('quantidade', 0)}</div>
                <div class="label">Convênios Ativos</div>
            </div>
        </div>

        <h2>Convênios</h2>
        <table>
            <thead>
                <tr>
                    <th>Número</th>
                    <th>Objeto</th>
                    <th>Órgão</th>
                    <th>Valor</th>
                    <th>Situação</th>
                </tr>
            </thead>
            <tbody>
        """

        for c in convenios.get("lista", [])[:10]:
            conteudo += f"""
                <tr>
                    <td>{c.get('numero', 'N/D')}</td>
                    <td>{c.get('objeto', 'N/D')[:50]}</td>
                    <td>{c.get('orgao', 'N/D')}</td>
                    <td>{format_currency(c.get('valorRepasse', c.get('valor', 0)))}</td>
                    <td>{c.get('situacao', 'N/D')}</td>
                </tr>
            """

        if not convenios.get("lista"):
            conteudo += "<tr><td colspan='5'>Nenhum convênio encontrado</td></tr>"

        conteudo += f"""
            </tbody>
        </table>

        <h2>Emendas Parlamentares</h2>
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="value">{format_currency(emendas.get('valorTotal', 0))}</div>
                <div class="label">Total em Emendas</div>
            </div>
            <div class="kpi-card">
                <div class="value">{emendas.get('quantidade', 0)}</div>
                <div class="label">Quantidade de Emendas</div>
            </div>
        </div>
        """

        # Renderizar e gerar PDF
        html = self._render_template(
            titulo="Relatório de Transferências Federais",
            subtitulo=f"Convênios e Emendas - {ano}",
            periodo=f"Ano {ano}",
            conteudo=conteudo,
            fontes=["Portal da Transparência Federal - CGU"]
        )

        filename = f"transferencias-{ano}-{datetime.now().strftime('%Y%m%d')}.pdf"
        return self._generate_pdf(html, filename)


class ConsolidatedReport(ReportGenerator):
    """Relatório consolidado com todas as fontes."""

    def generate(
        self,
        dados_fiscal: Dict[str, Any],
        dados_fornecedores: Dict[str, Any],
        dados_transferencias: Dict[str, Any],
        ano: int = None
    ) -> Optional[Path]:
        """
        Gera relatório consolidado.

        Args:
            dados_fiscal: Dados do SICONFI
            dados_fornecedores: Dados do TCE-SP
            dados_transferencias: Dados do Portal Federal
            ano: Ano de referência

        Returns:
            Caminho do arquivo gerado
        """
        ano = ano or datetime.now().year

        # Resumo executivo
        conteudo = """
        <h2>Sumário Executivo</h2>
        <div class="alert-box alert-info">
            Este relatório apresenta uma visão consolidada das finanças públicas do município
            de Marília, com dados de três fontes oficiais: SICONFI (indicadores fiscais),
            TCE-SP (execução orçamentária) e Portal Federal (transferências e convênios).
        </div>
        """

        # Seção fiscal
        rcl = dados_fiscal.get("rcl", 0)
        pessoal = dados_fiscal.get("despesaPessoal", {})

        conteudo += f"""
        <h2>Indicadores Fiscais (SICONFI)</h2>
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="value">{format_currency(rcl)}</div>
                <div class="label">Receita Corrente Líquida</div>
            </div>
            <div class="kpi-card">
                <div class="value">{format_percentage(pessoal.get('percentual', 0))}</div>
                <div class="label">Despesa com Pessoal (% RCL)</div>
            </div>
        </div>

        <div class="page-break"></div>
        """

        # Seção fornecedores
        fornecedores = dados_fornecedores.get("top10", dados_fornecedores.get("fornecedores", []))[:5]
        totais = dados_fornecedores.get("totais", {})

        conteudo += f"""
        <h2>Execução Orçamentária (TCE-SP)</h2>
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="value">{format_currency(totais.get('pago', 0))}</div>
                <div class="label">Total Pago</div>
            </div>
            <div class="kpi-card">
                <div class="value">{len(fornecedores)}</div>
                <div class="label">Maiores Fornecedores</div>
            </div>
        </div>

        <h3>Top 5 Fornecedores</h3>
        <table>
            <thead>
                <tr>
                    <th>Fornecedor</th>
                    <th>Valor</th>
                    <th>%</th>
                </tr>
            </thead>
            <tbody>
        """

        for f in fornecedores:
            conteudo += f"""
                <tr>
                    <td>{f.get('fornecedor', f.get('nome', 'N/D'))[:30]}</td>
                    <td>{format_currency(f.get('valor_total', f.get('valor', 0)))}</td>
                    <td>{format_percentage(f.get('percentual', 0))}</td>
                </tr>
            """

        conteudo += """
            </tbody>
        </table>

        <div class="page-break"></div>
        """

        # Seção transferências
        transferencias = dados_transferencias.get("transferencias", {})
        convenios = dados_transferencias.get("convenios", {})

        conteudo += f"""
        <h2>Recursos Federais (Portal Federal)</h2>
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="value">{format_currency(transferencias.get('total', 0))}</div>
                <div class="label">Transferências Recebidas</div>
            </div>
            <div class="kpi-card">
                <div class="value">{convenios.get('quantidade', 0)}</div>
                <div class="label">Convênios Ativos</div>
            </div>
        </div>
        """

        # Renderizar e gerar PDF
        html = self._render_template(
            titulo="Relatório Consolidado",
            subtitulo=f"Panorama Fiscal e Orçamentário - {ano}",
            periodo=f"Ano {ano}",
            conteudo=conteudo,
            fontes=[
                "SICONFI - Sistema de Informações Contábeis e Fiscais (Tesouro Nacional)",
                "TCE-SP - Tribunal de Contas do Estado de São Paulo",
                "Portal da Transparência Federal - CGU"
            ]
        )

        filename = f"consolidado-{ano}-{datetime.now().strftime('%Y%m%d')}.pdf"
        return self._generate_pdf(html, filename)


# Função de conveniência para gerar relatórios
def gerar_relatorio(
    tipo: str,
    dados: Dict[str, Any],
    output_dir: Path = None,
    ano: int = None
) -> Optional[Path]:
    """
    Gera um relatório do tipo especificado.

    Args:
        tipo: Tipo do relatório (fiscal, fornecedores, transferencias, consolidado)
        dados: Dados para o relatório
        output_dir: Diretório de saída
        ano: Ano de referência

    Returns:
        Caminho do arquivo gerado
    """
    generators = {
        "fiscal": FiscalReport,
        "fornecedores": SupplierReport,
        "transferencias": TransferReport,
    }

    if tipo not in generators:
        logger.error(f"Tipo de relatório inválido: {tipo}")
        return None

    generator = generators[tipo](output_dir)
    return generator.generate(dados, ano)
