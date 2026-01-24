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


# Template HTML base para relatórios
BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{{ titulo }}</title>
    <style>
        @page {
            size: A4;
            margin: 2cm;
            @top-center {
                content: "MonitoraMarília - {{ titulo }}";
                font-size: 9pt;
                color: #666;
            }
            @bottom-center {
                content: "Página " counter(page) " de " counter(pages);
                font-size: 9pt;
                color: #666;
            }
        }

        body {
            font-family: 'Helvetica', 'Arial', sans-serif;
            font-size: 11pt;
            line-height: 1.5;
            color: #333;
        }

        .header {
            background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
            color: white;
            padding: 20px;
            margin: -2cm -2cm 20px -2cm;
            text-align: center;
        }

        .header h1 {
            margin: 0;
            font-size: 24pt;
        }

        .header .subtitle {
            font-size: 12pt;
            opacity: 0.9;
        }

        .header .matra {
            font-size: 10pt;
            margin-top: 10px;
            opacity: 0.8;
        }

        .meta-info {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }

        .meta-info p {
            margin: 5px 0;
        }

        h2 {
            color: #1e3a5f;
            border-bottom: 2px solid #1e3a5f;
            padding-bottom: 5px;
            margin-top: 30px;
        }

        h3 {
            color: #2d5a87;
            margin-top: 20px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }

        th, td {
            border: 1px solid #ddd;
            padding: 10px;
            text-align: left;
        }

        th {
            background: #1e3a5f;
            color: white;
            font-weight: bold;
        }

        tr:nth-child(even) {
            background: #f9f9f9;
        }

        .status-ok {
            color: #10b981;
            font-weight: bold;
        }

        .status-alerta {
            color: #f59e0b;
            font-weight: bold;
        }

        .status-critico {
            color: #ef4444;
            font-weight: bold;
        }

        .alert-box {
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }

        .alert-info {
            background: #e0f2fe;
            border-left: 4px solid #0284c7;
        }

        .alert-warning {
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
        }

        .alert-danger {
            background: #fee2e2;
            border-left: 4px solid #ef4444;
        }

        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin: 20px 0;
        }

        .kpi-card {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
        }

        .kpi-card .value {
            font-size: 24pt;
            font-weight: bold;
            color: #1e3a5f;
        }

        .kpi-card .label {
            font-size: 10pt;
            color: #64748b;
        }

        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            font-size: 9pt;
            color: #666;
        }

        .footer .sources {
            margin-top: 10px;
        }

        .page-break {
            page-break-before: always;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ titulo }}</h1>
        <div class="subtitle">{{ subtitulo }}</div>
        <div class="matra">MATRA - Marília Transparente | Controle Social</div>
    </div>

    <div class="meta-info">
        <p><strong>Município:</strong> Marília - SP (IBGE: 3529005)</p>
        <p><strong>Período:</strong> {{ periodo }}</p>
        <p><strong>Gerado em:</strong> {{ data_geracao }}</p>
    </div>

    {{ conteudo }}

    <div class="footer">
        <p><strong>Nota:</strong> Este relatório foi gerado automaticamente pelo sistema MonitoraMarília
        com base em dados públicos oficiais. Os dados são atualizados conforme disponibilização pelas fontes.</p>
        <div class="sources">
            <strong>Fontes:</strong>
            <ul>
                {% for fonte in fontes %}
                <li>{{ fonte }}</li>
                {% endfor %}
            </ul>
        </div>
    </div>
</body>
</html>
"""


class ReportGenerator:
    """Classe base para geração de relatórios."""

    def __init__(self, output_dir: Path = None):
        """
        Inicializa o gerador de relatórios.

        Args:
            output_dir: Diretório para salvar os relatórios
        """
        self.output_dir = output_dir or DEFAULT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _render_template(
        self,
        titulo: str,
        subtitulo: str,
        periodo: str,
        conteudo: str,
        fontes: List[str]
    ) -> str:
        """Renderiza o template HTML com os dados."""
        template = Template(BASE_TEMPLATE)
        return template.render(
            titulo=titulo,
            subtitulo=subtitulo,
            periodo=periodo,
            data_geracao=datetime.now().strftime("%d/%m/%Y às %H:%M"),
            conteudo=conteudo,
            fontes=fontes
        )

    def _generate_pdf(self, html_content: str, filename: str) -> Optional[Path]:
        """
        Gera o PDF a partir do HTML.

        Args:
            html_content: Conteúdo HTML
            filename: Nome do arquivo PDF

        Returns:
            Caminho do arquivo gerado ou None se falhar
        """
        if not WEASYPRINT_AVAILABLE:
            logger.warning("WeasyPrint não disponível. Salvando apenas HTML.")
            html_path = self.output_dir / filename.replace(".pdf", ".html")
            html_path.write_text(html_content, encoding="utf-8")
            return html_path

        try:
            pdf_path = self.output_dir / filename
            HTML(string=html_content).write_pdf(pdf_path)
            logger.info(f"Relatório gerado: {pdf_path}")
            return pdf_path
        except Exception as e:
            logger.error(f"Erro ao gerar PDF: {e}")
            # Fallback para HTML
            html_path = self.output_dir / filename.replace(".pdf", ".html")
            html_path.write_text(html_content, encoding="utf-8")
            return html_path


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
