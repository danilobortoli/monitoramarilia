"""
Gerador de relatórios em PDF usando WeasyPrint.

Gera relatórios formatados para:
- Dados fiscais (SICONFI)
- Fornecedores (TCE-SP)
- Transferências federais
- Relatório consolidado
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from jinja2 import Template

logger = logging.getLogger(__name__)

# Diretório de saída dos relatórios
REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"


class PDFReporter:
    """Gerador de relatórios em PDF."""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Inicializa o gerador de relatórios.

        Args:
            output_dir: Diretório de saída (default: reports/)
        """
        self.output_dir = output_dir or REPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _format_currency(self, value: float) -> str:
        """Formata valor como moeda brasileira."""
        if value is None:
            return "N/D"
        if value >= 1_000_000:
            return f"R$ {value/1_000_000:.2f}M"
        elif value >= 1_000:
            return f"R$ {value/1_000:.2f}K"
        else:
            return f"R$ {value:.2f}"

    def _get_html_template(self, report_type: str) -> str:
        """Retorna template HTML para o tipo de relatório."""
        base_style = """
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; color: #333; }
            h1 { color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 10px; }
            h2 { color: #2c5282; margin-top: 30px; }
            h3 { color: #4a5568; }
            table { width: 100%; border-collapse: collapse; margin: 20px 0; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }
            th { background-color: #edf2f7; color: #1a365d; }
            tr:hover { background-color: #f7fafc; }
            .header { text-align: center; margin-bottom: 40px; }
            .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #718096; }
            .alert { background-color: #fed7d7; padding: 10px; border-radius: 5px; margin: 10px 0; }
            .ok { background-color: #c6f6d5; padding: 10px; border-radius: 5px; margin: 10px 0; }
            .warning { background-color: #fefcbf; padding: 10px; border-radius: 5px; margin: 10px 0; }
            .metric { display: inline-block; margin: 10px; padding: 20px; background: #edf2f7; border-radius: 8px; min-width: 150px; }
            .metric-value { font-size: 24px; font-weight: bold; color: #1a365d; }
            .metric-label { font-size: 14px; color: #718096; }
        </style>
        """

        templates = {
            "fiscal": base_style + """
            <div class="header">
                <h1>Relatorio Fiscal - {{ municipio }}</h1>
                <p>Ano de Referencia: {{ ano }} | Gerado em: {{ data_geracao }}</p>
            </div>

            <h2>Receita Corrente Liquida (RCL)</h2>
            <div class="metric">
                <div class="metric-value">{{ rcl_fmt }}</div>
                <div class="metric-label">RCL Anual</div>
            </div>

            <h2>Despesa com Pessoal</h2>
            <table>
                <tr>
                    <th>Indicador</th>
                    <th>Valor</th>
                    <th>% RCL</th>
                    <th>Limite</th>
                    <th>Status</th>
                </tr>
                {% for item in pessoal %}
                <tr>
                    <td>{{ item.indicador }}</td>
                    <td>{{ item.valor_fmt }}</td>
                    <td>{{ item.percentual }}%</td>
                    <td>{{ item.limite }}%</td>
                    <td class="{{ item.status_class }}">{{ item.status }}</td>
                </tr>
                {% endfor %}
            </table>

            <h2>Alertas LRF</h2>
            {% for alerta in alertas %}
            <div class="alert">
                <strong>{{ alerta.titulo }}</strong>: {{ alerta.descricao }}
            </div>
            {% else %}
            <div class="ok">Nenhum alerta fiscal identificado.</div>
            {% endfor %}

            <div class="footer">
                <p>Fonte: SICONFI - Tesouro Nacional | MonitoraMarilia - MATRA</p>
            </div>
            """,

            "suppliers": base_style + """
            <div class="header">
                <h1>Relatorio de Fornecedores - {{ municipio }}</h1>
                <p>Ano de Referencia: {{ ano }} | Gerado em: {{ data_geracao }}</p>
            </div>

            <h2>Resumo</h2>
            <div class="metric">
                <div class="metric-value">{{ total_fornecedores }}</div>
                <div class="metric-label">Fornecedores Analisados</div>
            </div>
            <div class="metric">
                <div class="metric-value">{{ total_pago_fmt }}</div>
                <div class="metric-label">Total Pago</div>
            </div>

            <h2>Maiores Fornecedores</h2>
            <table>
                <tr>
                    <th>#</th>
                    <th>Fornecedor</th>
                    <th>CNPJ</th>
                    <th>Valor Total</th>
                    <th>Pagamentos</th>
                    <th>% Total</th>
                </tr>
                {% for f in fornecedores %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td>{{ f.nome }}</td>
                    <td>{{ f.cnpj }}</td>
                    <td>{{ f.valor_fmt }}</td>
                    <td>{{ f.qtd_pagamentos }}</td>
                    <td>{{ f.percentual }}%</td>
                </tr>
                {% endfor %}
            </table>

            <h2>Alertas de Concentracao</h2>
            {% for alerta in alertas %}
            <div class="warning">
                <strong>{{ alerta.fornecedor }}</strong>: Concentracao de {{ alerta.percentual }}% dos pagamentos
            </div>
            {% else %}
            <div class="ok">Nenhuma concentracao excessiva identificada.</div>
            {% endfor %}

            <div class="footer">
                <p>Fonte: TCE-SP | MonitoraMarilia - MATRA</p>
            </div>
            """,

            "transfers": base_style + """
            <div class="header">
                <h1>Relatorio de Transferencias Federais - {{ municipio }}</h1>
                <p>Ano de Referencia: {{ ano }} | Gerado em: {{ data_geracao }}</p>
            </div>

            <h2>Resumo de Transferencias</h2>
            <div class="metric">
                <div class="metric-value">{{ total_transferencias_fmt }}</div>
                <div class="metric-label">Total Recebido</div>
            </div>
            <div class="metric">
                <div class="metric-value">{{ qtd_convenios }}</div>
                <div class="metric-label">Convenios Ativos</div>
            </div>

            <h2>Transferencias por Tipo</h2>
            <table>
                <tr>
                    <th>Tipo</th>
                    <th>Valor</th>
                    <th>% Total</th>
                </tr>
                {% for t in transferencias_por_tipo %}
                <tr>
                    <td>{{ t.tipo }}</td>
                    <td>{{ t.valor_fmt }}</td>
                    <td>{{ t.percentual }}%</td>
                </tr>
                {% endfor %}
            </table>

            <h2>Convenios</h2>
            <table>
                <tr>
                    <th>Numero</th>
                    <th>Objeto</th>
                    <th>Valor</th>
                    <th>Situacao</th>
                </tr>
                {% for c in convenios %}
                <tr>
                    <td>{{ c.numero }}</td>
                    <td>{{ c.objeto }}</td>
                    <td>{{ c.valor_fmt }}</td>
                    <td>{{ c.situacao }}</td>
                </tr>
                {% endfor %}
            </table>

            <div class="footer">
                <p>Fonte: Portal da Transparencia Federal | MonitoraMarilia - MATRA</p>
            </div>
            """,

            "consolidated": base_style + """
            <div class="header">
                <h1>Relatorio Consolidado - {{ municipio }}</h1>
                <p>Ano de Referencia: {{ ano }} | Gerado em: {{ data_geracao }}</p>
            </div>

            <h2>Visao Geral</h2>
            <div class="metric">
                <div class="metric-value">{{ rcl_fmt }}</div>
                <div class="metric-label">RCL</div>
            </div>
            <div class="metric">
                <div class="metric-value">{{ despesa_pessoal }}%</div>
                <div class="metric-label">Despesa Pessoal/RCL</div>
            </div>
            <div class="metric">
                <div class="metric-value">{{ total_pago_fmt }}</div>
                <div class="metric-label">Total Pago</div>
            </div>

            <h2>Indicadores Fiscais</h2>
            <table>
                <tr>
                    <th>Indicador</th>
                    <th>Valor</th>
                    <th>% RCL</th>
                    <th>Status</th>
                </tr>
                {% for i in indicadores %}
                <tr>
                    <td>{{ i.nome }}</td>
                    <td>{{ i.valor_fmt }}</td>
                    <td>{{ i.percentual }}%</td>
                    <td class="{{ i.status_class }}">{{ i.status }}</td>
                </tr>
                {% endfor %}
            </table>

            <h2>Top 10 Fornecedores</h2>
            <table>
                <tr>
                    <th>#</th>
                    <th>Fornecedor</th>
                    <th>Valor</th>
                    <th>% Total</th>
                </tr>
                {% for f in fornecedores[:10] %}
                <tr>
                    <td>{{ loop.index }}</td>
                    <td>{{ f.nome }}</td>
                    <td>{{ f.valor_fmt }}</td>
                    <td>{{ f.percentual }}%</td>
                </tr>
                {% endfor %}
            </table>

            <h2>Alertas</h2>
            {% for alerta in alertas %}
            <div class="alert">
                <strong>{{ alerta.tipo }}</strong>: {{ alerta.descricao }}
            </div>
            {% else %}
            <div class="ok">Nenhum alerta identificado.</div>
            {% endfor %}

            <div class="footer">
                <p>Fontes: SICONFI, TCE-SP, Portal Federal | MonitoraMarilia - MATRA</p>
            </div>
            """
        }

        return templates.get(report_type, templates["consolidated"])

    def generate_fiscal_report(
        self,
        ano: int,
        fiscal_data: Dict[str, Any],
        municipio: str = "Marilia"
    ) -> Optional[Path]:
        """
        Gera relatório fiscal em PDF.

        Args:
            ano: Ano de referência
            fiscal_data: Dados fiscais coletados
            municipio: Nome do município

        Returns:
            Caminho do arquivo gerado ou None em caso de erro
        """
        try:
            # Preparar dados do template
            resumo = fiscal_data.get("resumo", {})
            indicadores = resumo.get("indicadores", {})
            rcl = indicadores.get("rcl", {}).get("valor", 0)
            alertas = fiscal_data.get("alertas_lrf", [])

            pessoal_items = []
            for key, data in indicadores.items():
                if "pessoal" in key.lower():
                    status = "OK" if data.get("percentual_rcl", 0) < data.get("limite", 100) else "ALERTA"
                    pessoal_items.append({
                        "indicador": data.get("nome", key),
                        "valor_fmt": self._format_currency(data.get("valor", 0)),
                        "percentual": f"{data.get('percentual_rcl', 0):.1f}",
                        "limite": data.get("limite", 0),
                        "status": status,
                        "status_class": "ok" if status == "OK" else "alert"
                    })

            context = {
                "municipio": municipio,
                "ano": ano,
                "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "rcl_fmt": self._format_currency(rcl),
                "pessoal": pessoal_items or [{"indicador": "N/D", "valor_fmt": "N/D", "percentual": "N/D", "limite": "54", "status": "N/D", "status_class": ""}],
                "alertas": [{"titulo": a.get("titulo", ""), "descricao": a.get("descricao", "")} for a in alertas]
            }

            # Renderizar template
            template = Template(self._get_html_template("fiscal"))
            html_content = template.render(**context)

            # Gerar PDF
            output_path = self.output_dir / f"relatorio_fiscal_{municipio.lower()}_{ano}.pdf"

            try:
                from weasyprint import HTML
                HTML(string=html_content).write_pdf(output_path)
                logger.info(f"Relatorio fiscal gerado: {output_path}")
            except ImportError:
                # Fallback: salvar como HTML se WeasyPrint nao disponivel
                output_path = output_path.with_suffix(".html")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.warning(f"WeasyPrint nao disponivel. Relatorio salvo como HTML: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Erro ao gerar relatorio fiscal: {e}")
            return None

    def generate_suppliers_report(
        self,
        ano: int,
        fornecedores: List[Dict[str, Any]],
        alertas: List[Dict[str, Any]] = None,
        municipio: str = "Marilia"
    ) -> Optional[Path]:
        """
        Gera relatório de fornecedores em PDF.

        Args:
            ano: Ano de referência
            fornecedores: Lista de fornecedores
            alertas: Alertas de concentração
            municipio: Nome do município

        Returns:
            Caminho do arquivo gerado ou None em caso de erro
        """
        try:
            total_pago = sum(f.get("valor_total", f.get("valor", 0)) or 0 for f in fornecedores)

            fornecedores_fmt = []
            for f in fornecedores[:20]:
                valor = f.get("valor_total", f.get("valor", 0)) or 0
                percentual = (valor / total_pago * 100) if total_pago > 0 else 0
                fornecedores_fmt.append({
                    "nome": f.get("fornecedor", f.get("nome", "N/D")),
                    "cnpj": f.get("cnpj_parcial", f.get("cnpj", "N/D")),
                    "valor_fmt": self._format_currency(valor),
                    "qtd_pagamentos": f.get("qtd_pagamentos", 0),
                    "percentual": f"{percentual:.1f}"
                })

            context = {
                "municipio": municipio,
                "ano": ano,
                "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "total_fornecedores": len(fornecedores),
                "total_pago_fmt": self._format_currency(total_pago),
                "fornecedores": fornecedores_fmt,
                "alertas": alertas or []
            }

            template = Template(self._get_html_template("suppliers"))
            html_content = template.render(**context)

            output_path = self.output_dir / f"relatorio_fornecedores_{municipio.lower()}_{ano}.pdf"

            try:
                from weasyprint import HTML
                HTML(string=html_content).write_pdf(output_path)
                logger.info(f"Relatorio de fornecedores gerado: {output_path}")
            except ImportError:
                output_path = output_path.with_suffix(".html")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.warning(f"WeasyPrint nao disponivel. Relatorio salvo como HTML: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Erro ao gerar relatorio de fornecedores: {e}")
            return None

    def generate_transfers_report(
        self,
        ano: int,
        federal_data: Dict[str, Any],
        municipio: str = "Marilia"
    ) -> Optional[Path]:
        """
        Gera relatório de transferências federais em PDF.

        Args:
            ano: Ano de referência
            federal_data: Dados do portal federal
            municipio: Nome do município

        Returns:
            Caminho do arquivo gerado ou None em caso de erro
        """
        try:
            transferencias = federal_data.get("transferencias", {})
            convenios = federal_data.get("convenios", {})

            por_tipo = []
            total = transferencias.get("valor_total", 0) or 0
            for tipo, valor in transferencias.get("por_tipo", {}).items():
                percentual = (valor / total * 100) if total > 0 else 0
                por_tipo.append({
                    "tipo": tipo,
                    "valor_fmt": self._format_currency(valor),
                    "percentual": f"{percentual:.1f}"
                })

            convenios_list = []
            for c in convenios.get("lista", [])[:10]:
                convenios_list.append({
                    "numero": c.get("numero", "N/D"),
                    "objeto": c.get("objeto", "N/D")[:80] + "..." if len(c.get("objeto", "")) > 80 else c.get("objeto", "N/D"),
                    "valor_fmt": self._format_currency(c.get("valor_repasse", 0)),
                    "situacao": c.get("situacao", "N/D")
                })

            context = {
                "municipio": municipio,
                "ano": ano,
                "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "total_transferencias_fmt": self._format_currency(total),
                "qtd_convenios": convenios.get("quantidade", 0),
                "transferencias_por_tipo": por_tipo,
                "convenios": convenios_list
            }

            template = Template(self._get_html_template("transfers"))
            html_content = template.render(**context)

            output_path = self.output_dir / f"relatorio_transferencias_{municipio.lower()}_{ano}.pdf"

            try:
                from weasyprint import HTML
                HTML(string=html_content).write_pdf(output_path)
                logger.info(f"Relatorio de transferencias gerado: {output_path}")
            except ImportError:
                output_path = output_path.with_suffix(".html")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.warning(f"WeasyPrint nao disponivel. Relatorio salvo como HTML: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Erro ao gerar relatorio de transferencias: {e}")
            return None

    def generate_consolidated_report(
        self,
        ano: int,
        fiscal_data: Dict[str, Any],
        tce_data: Dict[str, Any],
        federal_data: Dict[str, Any] = None,
        municipio: str = "Marilia"
    ) -> Optional[Path]:
        """
        Gera relatório consolidado com dados de todas as fontes.

        Args:
            ano: Ano de referência
            fiscal_data: Dados fiscais (SICONFI)
            tce_data: Dados do TCE-SP
            federal_data: Dados do portal federal (opcional)
            municipio: Nome do município

        Returns:
            Caminho do arquivo gerado ou None em caso de erro
        """
        try:
            # Extrair dados fiscais
            resumo = fiscal_data.get("resumo", {})
            indicadores_raw = resumo.get("indicadores", {})
            rcl = indicadores_raw.get("rcl", {}).get("valor", 0)
            alertas_lrf = fiscal_data.get("alertas_lrf", [])

            # Calcular despesa com pessoal
            despesa_pessoal = 0
            for alerta in alertas_lrf:
                if alerta.get("categoria") == "pessoal":
                    despesa_pessoal = alerta.get("valor", 0)
                    break

            # Indicadores formatados
            indicadores = []
            for key, data in indicadores_raw.items():
                if isinstance(data, dict) and data.get("valor"):
                    status = "OK"
                    if data.get("percentual_rcl") and data.get("limite"):
                        status = "ALERTA" if data.get("percentual_rcl", 0) >= data.get("limite", 100) else "OK"
                    indicadores.append({
                        "nome": data.get("nome", key),
                        "valor_fmt": self._format_currency(data.get("valor", 0)),
                        "percentual": f"{data.get('percentual_rcl', 0):.1f}" if data.get("percentual_rcl") else "N/A",
                        "status": status,
                        "status_class": "ok" if status == "OK" else "alert"
                    })

            # Fornecedores
            fornecedores_raw = tce_data.get("fornecedores", [])
            total_pago = tce_data.get("totais", {}).get("pago", 0)

            fornecedores = []
            for f in fornecedores_raw[:10]:
                valor = f.get("valor_total", 0)
                percentual = (valor / total_pago * 100) if total_pago > 0 else 0
                fornecedores.append({
                    "nome": f.get("fornecedor", "N/D"),
                    "valor_fmt": self._format_currency(valor),
                    "percentual": f"{percentual:.1f}"
                })

            # Alertas consolidados
            alertas = []
            for a in alertas_lrf:
                alertas.append({
                    "tipo": "LRF",
                    "descricao": a.get("descricao", a.get("titulo", ""))
                })
            for a in tce_data.get("alertas_concentracao", []):
                alertas.append({
                    "tipo": "Fornecedor",
                    "descricao": f"{a.get('fornecedor', 'N/D')}: {a.get('percentual', 0):.1f}% dos pagamentos"
                })

            context = {
                "municipio": municipio,
                "ano": ano,
                "data_geracao": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "rcl_fmt": self._format_currency(rcl),
                "despesa_pessoal": f"{despesa_pessoal:.1f}",
                "total_pago_fmt": self._format_currency(total_pago),
                "indicadores": indicadores,
                "fornecedores": fornecedores,
                "alertas": alertas
            }

            template = Template(self._get_html_template("consolidated"))
            html_content = template.render(**context)

            output_path = self.output_dir / f"relatorio_consolidado_{municipio.lower()}_{ano}.pdf"

            try:
                from weasyprint import HTML
                HTML(string=html_content).write_pdf(output_path)
                logger.info(f"Relatorio consolidado gerado: {output_path}")
            except ImportError:
                output_path = output_path.with_suffix(".html")
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                logger.warning(f"WeasyPrint nao disponivel. Relatorio salvo como HTML: {output_path}")

            return output_path

        except Exception as e:
            logger.error(f"Erro ao gerar relatorio consolidado: {e}")
            return None
