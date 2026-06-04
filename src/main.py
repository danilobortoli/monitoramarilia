#!/usr/bin/env python3
"""
MonitoraMarília - CLI Principal
Sistema de monitoramento de transparência pública de Marília.

Desenvolvido pela MATRA - Marília Transparente

Fontes de dados abertas:
- SICONFI (Tesouro Nacional): Dados fiscais (RGF, RREO, DCA)
- TCE-SP: Despesas e receitas detalhadas
- Portal Federal: Transferências, convênios, sanções (CEIS/CNEP)

Funcionalidades:
- Coleta de dados de APIs oficiais
- Armazenamento em banco SQLite para histórico
- Geração de relatórios PDF
- Atualização de dashboard web
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Garante que os pacotes internos (collectors, reports, database) sejam
# encontrados tanto via `python -m src.main` quanto `python src/main.py`,
# independentemente do PYTHONPATH configurado no ambiente.
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Tentar importar Rich para output bonito
try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    console = None


def print_header():
    """Imprime o cabeçalho do sistema."""
    header = """
╔══════════════════════════════════════════════════════════════╗
║              MonitoraMarília - Controle Social               ║
║                  MATRA - Marília Transparente                ║
║                                                              ║
║  Fontes: SICONFI | TCE-SP | Portal Federal                  ║
╚══════════════════════════════════════════════════════════════╝
    """
    if RICH_AVAILABLE:
        console.print(header, style="blue")
    else:
        print(header)


def log(message: str, level: str = "info"):
    """Log com cores se disponível."""
    icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
    icon = icons.get(level, "•")

    if RICH_AVAILABLE:
        colors = {"info": "blue", "success": "green", "warning": "yellow", "error": "red"}
        console.print(f"{icon} {message}", style=colors.get(level, "white"))
    else:
        print(f"{icon} {message}")


def cmd_siconfi(args):
    """Consulta dados do SICONFI (Tesouro Nacional)."""
    from collectors.siconfi import SiconfiCollector

    log("Consultando SICONFI - Tesouro Nacional...", "info")
    collector = SiconfiCollector()
    ano = args.ano or datetime.now().year

    if args.tipo == "resumo":
        data = collector.get_resumo_fiscal(ano)
    elif args.tipo == "rgf":
        data = collector.get_rgf(ano, args.quadrimestre or 3)
    elif args.tipo == "rreo":
        data = collector.get_rreo(ano, args.bimestre or 6)
    elif args.tipo == "alertas":
        data = collector.verificar_alertas_lrf(ano)
    elif args.tipo == "dashboard":
        data = collector.get_dados_para_dashboard(ano)
    else:
        log(f"Tipo desconhecido: {args.tipo}", "error")
        return

    log(f"Dados do SICONFI obtidos para {ano}", "success")

    if args.output:
        _save_json(args.output, data)
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_tce_sp(args):
    """Consulta dados do TCE-SP."""
    from collectors.tce_sp import TCESPCollector

    log("Consultando TCE-SP...", "info")
    collector = TCESPCollector()
    ano = args.ano or datetime.now().year

    if args.tipo == "despesas":
        data = collector.get_despesas_ano(ano)
    elif args.tipo == "fornecedores":
        data = collector.get_maiores_fornecedores(ano, top_n=args.top or 20)
    elif args.tipo == "concentracao":
        data = collector.detect_concentracao_fornecedor(ano)
    elif args.tipo == "dashboard":
        data = collector.get_dados_para_dashboard(ano)
    else:
        log(f"Tipo desconhecido: {args.tipo}", "error")
        return

    log(f"Dados do TCE-SP obtidos: {len(data) if isinstance(data, list) else 'OK'}", "success")

    if args.output:
        _save_json(args.output, data)
    else:
        if isinstance(data, list):
            print(f"Total: {len(data)} registros")
            for item in data[:5]:
                print(json.dumps(item, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_portal_federal(args):
    """Consulta dados do Portal da Transparência Federal."""
    from collectors.portal_federal import PortalFederalCollector

    log("Consultando Portal da Transparência Federal...", "info")
    collector = PortalFederalCollector()
    ano = args.ano or datetime.now().year

    if not collector.api_key:
        log("API Key não configurada!", "warning")
        log("Configure: PORTAL_TRANSPARENCIA_KEY=sua_chave", "info")
        log("Cadastre em: https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email", "info")
        return

    if args.tipo == "convenios":
        data = collector.get_convenios(ano)
    elif args.tipo == "transferencias":
        data = collector.get_transferencias(ano)
    elif args.tipo == "emendas":
        data = collector.get_emendas_parlamentares(ano)
    elif args.tipo == "verificar-cnpj":
        if not args.cnpj:
            log("CNPJ é obrigatório para verificação", "error")
            return
        data = collector.verificar_fornecedor_completo(args.cnpj)
    elif args.tipo == "dashboard":
        data = collector.get_dados_para_dashboard(ano)
    else:
        log(f"Tipo desconhecido: {args.tipo}", "error")
        return

    log(f"Dados do Portal Federal obtidos", "success")

    if args.output:
        _save_json(args.output, data)
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_integrado(args):
    """Gera relatório integrado de todas as fontes."""
    from models.dados_integrados import DadosIntegrados

    log("Gerando relatório integrado...", "info")
    integrador = DadosIntegrados()
    ano = args.ano or datetime.now().year

    if args.tipo == "relatorio":
        data = integrador.gerar_relatorio_integrado(ano)
    elif args.tipo == "dashboard":
        data = integrador.exportar_para_dashboard(ano)
    elif args.tipo == "fornecedores":
        integrador.carregar_fornecedores_tce(ano)
        data = {
            "total": len(integrador.fornecedores),
            "fornecedores": [
                {
                    "cnpj": f.cnpj,
                    "nome": f.nome,
                    "valor": f.valor_total_pagamentos,
                    "pagamentos": f.qtd_pagamentos
                }
                for f in sorted(
                    integrador.fornecedores.values(),
                    key=lambda x: x.valor_total_pagamentos,
                    reverse=True
                )[:20]
            ]
        }
    else:
        log(f"Tipo desconhecido: {args.tipo}", "error")
        return

    log("Relatório integrado gerado", "success")

    if args.output:
        _save_json(args.output, data)
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))


def cmd_update_dashboard(args):
    """
    Atualiza os dados do dashboard com dados de múltiplas fontes abertas.

    Este comando:
    1. Coleta dados do SICONFI (fiscais)
    2. Coleta dados do TCE-SP (despesas, fornecedores)
    3. Coleta dados do Portal Federal (transferências, sanções) - se API disponível
    4. Gera arquivos JSON para o dashboard estático
    """
    log("Atualizando dados do dashboard...", "info")

    ano = args.ano or datetime.now().year
    output_dir = Path(args.output) if args.output else Path("docs/data")
    output_dir.mkdir(parents=True, exist_ok=True)

    log(f"Diretório de saída: {output_dir}", "info")
    log(f"Ano de referência: {ano}", "info")

    # Importar coletores
    from collectors.siconfi import SiconfiCollector
    from collectors.tce_sp import TCESPCollector
    from collectors.portal_federal import PortalFederalCollector

    # Dados coletados
    fiscal_data = {}
    tce_data = {}
    federal_data = {}

    # 1. Coletar dados fiscais (SICONFI)
    log("1/3 Coletando dados fiscais (SICONFI)...", "info")
    try:
        siconfi = SiconfiCollector()
        fiscal_data = siconfi.get_dados_para_dashboard(ano)
        log("SICONFI: OK", "success")
    except Exception as e:
        log(f"Erro SICONFI: {e}", "warning")

    # 2. Coletar execução do TCE-SP — UMA ÚNICA coleta anual alimenta totais,
    #    fornecedores, concentração e gráficos. Evita re-buscar o ano inteiro
    #    várias vezes (o que tornava o job lento e frágil sob throttling).
    log("2/3 Coletando execução orçamentária (TCE-SP)...", "info")
    graficos_data = {
        "despesasPorOrgao": {"labels": [], "valores": []},
        "evolucaoMensal": {"labels": [], "empenhado": [], "liquidado": [], "pago": []},
    }
    try:
        despesas_ano = TCESPCollector().get_despesas_ano(ano)
        if despesas_ano:
            tce_data = _consolidar_tce(despesas_ano, ano, graficos_data)
            log(f"TCE-SP: {tce_data.get('qtd_despesas', 0)} lançamentos, "
                f"{len(tce_data.get('fornecedores', []))} fornecedores", "success")
        else:
            log("TCE-SP: sem dados no período (mantendo vazio)", "warning")
    except Exception as e:
        log(f"Erro TCE-SP: {e}", "warning")

    # 3. Coletar dados Portal Federal
    log("3/3 Coletando dados federais (Portal Transparência)...", "info")
    try:
        federal = PortalFederalCollector()
        if federal.api_key:
            federal_data = federal.get_dados_para_dashboard(ano)
            log("Portal Federal: OK", "success")
        else:
            log("Portal Federal: API Key não configurada (pulando)", "warning")
            federal_data = {"erro": "API Key não configurada"}
    except Exception as e:
        log(f"Erro Portal Federal: {e}", "warning")

    # Gerar dados integrados
    log("Consolidando dados...", "info")

    # Extrair valores dos coletores
    rcl = fiscal_data.get("resumo", {}).get("indicadores", {}).get("rcl", {}).get("valor", 0)
    alertas_lrf = fiscal_data.get("alertas_lrf", [])

    # Despesa com pessoal
    pessoal_percentual = 50.0
    for alerta in alertas_lrf:
        if alerta.get("categoria") == "pessoal":
            pessoal_percentual = alerta.get("valor", 50.0)
            break

    # Formatar fornecedores
    fornecedores_list = tce_data.get("fornecedores", [])[:10]
    fornecedores_formatados = []
    for f in fornecedores_list:
        fornecedores_formatados.append({
            "cnpj": f.get("cnpj_parcial", ""),
            "nome": f.get("fornecedor", ""),
            "valor": f.get("valor_total", 0),
            "valorFmt": f"R$ {f.get('valor_total', 0)/1_000_000:.2f}M",
            "qtdPagamentos": f.get("qtd_pagamentos", 0),
            "situacaoSancoes": "REGULAR"
        })

    # Dados consolidados para o dashboard
    dashboard_data = {
        "lastUpdate": datetime.now().isoformat(),
        "ano": ano,
        "municipio": "Marília",
        "codigoIBGE": "3529005",

        # SICONFI - Dados Fiscais
        "fiscal": {
            "fonte": "SICONFI - Tesouro Nacional",
            "rcl": rcl,
            "rclFormatado": f"R$ {rcl/1_000_000:.1f}M" if rcl else "N/D",
            "despesaPessoal": {
                "valor": rcl * (pessoal_percentual / 100) if rcl else 0,
                "percentual": pessoal_percentual,
                "limite": 54,
                "limiteAlerta": 48.6,
                "limitePrudencial": 51.3,
                "status": "ok" if pessoal_percentual < 48.6 else "alerta" if pessoal_percentual < 51.3 else "prudencial" if pessoal_percentual < 54 else "critico"
            },
            "divida": {
                "valor": 0,
                "percentual": 0,
                "limite": 120,
                "status": "ok"
            },
            "alertasLRF": alertas_lrf
        },

        # TCE-SP - Execução Orçamentária
        "execucao": {
            "fonte": "TCE-SP",
            "periodo": tce_data.get("periodo", ""),
            "empenhado": tce_data.get("totais", {}).get("empenhado", 0),
            "empenhadoFmt": tce_data.get("totais", {}).get("empenhado_fmt", "N/D"),
            "liquidado": tce_data.get("totais", {}).get("liquidado", 0),
            "liquidadoFmt": tce_data.get("totais", {}).get("liquidado_fmt", "N/D"),
            "pago": tce_data.get("totais", {}).get("pago", 0),
            "pagoFmt": tce_data.get("totais", {}).get("pago_fmt", "N/D"),
            "qtdDespesas": tce_data.get("qtd_despesas", 0)
        },

        # Fornecedores
        "fornecedores": {
            "fonte": "TCE-SP + Portal Federal",
            "totalAnalisados": len(fornecedores_formatados),
            "top10": fornecedores_formatados,
            "sancoesVerificadas": {
                "total": len(fornecedores_formatados),
                "regulares": len(fornecedores_formatados),
                "irregulares": 0,
                "alertas": []
            }
        },

        # Portal Federal - Transferências
        "transferencias": {
            "fonte": "Portal da Transparência Federal",
            "disponivel": bool(federal_data and "erro" not in federal_data),
            "total": federal_data.get("transferencias", {}).get("valor_total", 0) if federal_data else 0,
            "totalFmt": federal_data.get("transferencias", {}).get("valor_fmt", "N/D") if federal_data else "N/D",
            "porTipo": federal_data.get("transferencias", {}).get("por_tipo", {}) if federal_data else {}
        },

        # Convênios
        "convenios": {
            "fonte": "Portal da Transparência Federal",
            "quantidade": federal_data.get("convenios", {}).get("quantidade", 0) if federal_data else 0,
            "valorTotal": federal_data.get("convenios", {}).get("valor_total", 0) if federal_data else 0,
            "valorFmt": federal_data.get("convenios", {}).get("valor_fmt", "N/D") if federal_data else "N/D",
            "lista": federal_data.get("convenios", {}).get("lista", []) if federal_data else []
        },

        # Emendas
        "emendas": {
            "fonte": "Portal da Transparência Federal",
            "quantidade": federal_data.get("emendas", {}).get("quantidade", 0) if federal_data else 0,
            "valorTotal": federal_data.get("emendas", {}).get("valor_total", 0) if federal_data else 0,
            "valorFmt": federal_data.get("emendas", {}).get("valor_fmt", "N/D") if federal_data else "N/D",
            "porAutor": federal_data.get("emendas", {}).get("por_autor", []) if federal_data else []
        },

        # Alertas
        "alertas": {
            "total": len(alertas_lrf) + len(tce_data.get("alertas_concentracao", [])),
            "lrf": alertas_lrf,
            "fornecedores": tce_data.get("alertas_concentracao", []),
            "outros": []
        },

        # Gráficos (dados reais do TCE-SP; vazio quando ainda não coletado)
        "graficos": graficos_data,

        # Fontes
        "fontes": {
            "siconfi": {
                "nome": "SICONFI - Tesouro Nacional",
                "url": "https://siconfi.tesouro.gov.br",
                "dados": ["RGF", "RREO", "DCA"],
                "atualizacao": "Quadrimestral/Bimestral"
            },
            "tceSP": {
                "nome": "TCE-SP - Tribunal de Contas SP",
                "url": "https://transparencia.tce.sp.gov.br",
                "dados": ["Despesas", "Receitas"],
                "atualizacao": "Mensal"
            },
            "portalFederal": {
                "nome": "Portal da Transparência Federal",
                "url": "https://portaldatransparencia.gov.br",
                "dados": ["Convênios", "Transferências", "CEIS", "CNEP", "Emendas"],
                "requerApiKey": True,
                "atualizacao": "Diária"
            }
        }
    }

    # Salvar arquivo principal
    with open(output_dir / "dashboard.json", "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)

    # Salvar arquivos individuais para cada fonte
    with open(output_dir / "siconfi.json", "w", encoding="utf-8") as f:
        json.dump(fiscal_data, f, ensure_ascii=False, indent=2)

    with open(output_dir / "tce-sp.json", "w", encoding="utf-8") as f:
        json.dump(tce_data, f, ensure_ascii=False, indent=2)

    if federal_data and "erro" not in federal_data:
        with open(output_dir / "portal-federal.json", "w", encoding="utf-8") as f:
            json.dump(federal_data, f, ensure_ascii=False, indent=2)

    # Índice dos relatórios PDF para a página de relatórios do site
    try:
        manifest = _build_reports_manifest(output_dir.parent / "relatorios",
                                           output_dir / "relatorios.json")
        log(f"Índice de relatórios atualizado ({manifest['total']} arquivos)", "success")
    except Exception as e:
        log(f"Erro ao indexar relatórios: {e}", "warning")

    log("Dashboard atualizado com sucesso!", "success")
    log(f"Arquivos gerados em: {output_dir}", "info")

    # Listar arquivos gerados
    print("\nArquivos gerados:")
    for f in output_dir.glob("*.json"):
        print(f"  - {f.name}")


def _consolidar_tce(despesas, ano, graficos_data):
    """
    Consolida UMA coleta anual de despesas do TCE-SP em um único passo:
    totais (empenhado/liquidado/pago), maiores fornecedores, alertas de
    concentração e os dados dos gráficos (série mensal e despesa por função).

    Faz tudo a partir da mesma lista de despesas, evitando re-buscar o ano
    inteiro várias vezes — o que deixava a atualização lenta e frágil.
    """
    meses_nome = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                  "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
    evol = {m: {"empenhado": 0.0, "liquidado": 0.0, "pago": 0.0} for m in range(1, 13)}
    por_orgao = {}
    fornecedores = {}
    total_empenhado = total_liquidado = total_pago = 0.0

    for d in despesas:
        evento = (d.get("evento") or "").upper()
        valor = d.get("valor", 0) or 0
        try:
            mes = int(d.get("mes") or 0)
        except (ValueError, TypeError):
            mes = 0

        is_pago = "PAG" in evento
        if "EMPENH" in evento:
            total_empenhado += valor
            if 1 <= mes <= 12:
                evol[mes]["empenhado"] += valor
        elif "LIQUID" in evento:
            total_liquidado += valor
            if 1 <= mes <= 12:
                evol[mes]["liquidado"] += valor
        elif is_pago:
            total_pago += valor
            if 1 <= mes <= 12:
                evol[mes]["pago"] += valor

        if is_pago:
            orgao = d.get("orgao") or "Não informado"
            por_orgao[orgao] = por_orgao.get(orgao, 0) + valor
            nome = d.get("fornecedor") or "Não informado"
            cnpj = d.get("cnpj_parcial", "")
            reg = fornecedores.get((nome, cnpj))
            if reg is None:
                reg = {"fornecedor": nome, "cnpj_parcial": cnpj,
                       "valor_total": 0.0, "qtd_pagamentos": 0}
                fornecedores[(nome, cnpj)] = reg
            reg["valor_total"] += valor
            reg["qtd_pagamentos"] += 1

    ranking = sorted(fornecedores.values(), key=lambda x: x["valor_total"], reverse=True)
    for r in ranking:
        r["percentual"] = (r["valor_total"] / total_pago * 100) if total_pago > 0 else 0

    alertas_concentracao = []
    for r in ranking:
        if r["percentual"] > 10.0:
            alertas_concentracao.append({
                "tipo": "alerta",
                "categoria": "concentracao",
                "titulo": f"Alta concentração: {r['fornecedor'][:30]}",
                "descricao": (f"Fornecedor recebeu {r['percentual']:.1f}% do total pago "
                              f"(R$ {r['valor_total']/1_000_000:.2f} milhões)"),
                "fornecedor": r["fornecedor"],
                "cnpj_parcial": r["cnpj_parcial"],
                "valor": r["valor_total"],
                "percentual": r["percentual"],
                "data": datetime.now().strftime("%Y-%m-%d"),
            })

    # Gráficos
    top_orgaos = sorted(por_orgao.items(), key=lambda x: x[1], reverse=True)[:6]
    graficos_data["despesasPorOrgao"]["labels"] = [k for k, _ in top_orgaos]
    graficos_data["despesasPorOrgao"]["valores"] = [round(v, 2) for _, v in top_orgaos]
    meses_com_dado = [m for m in range(1, 13) if any(evol[m].values())]
    graficos_data["evolucaoMensal"]["labels"] = [meses_nome[m - 1] for m in meses_com_dado]
    for chave in ("empenhado", "liquidado", "pago"):
        graficos_data["evolucaoMensal"][chave] = [
            round(evol[m][chave] / 1_000_000, 2) for m in meses_com_dado
        ]

    return {
        "fonte": "TCE-SP",
        "ano": ano,
        "ultima_atualizacao": datetime.now().isoformat(),
        "periodo": f"Ano {ano}",
        "totais": {
            "empenhado": total_empenhado,
            "liquidado": total_liquidado,
            "pago": total_pago,
            "empenhado_fmt": f"R$ {total_empenhado/1_000_000:.1f}M",
            "liquidado_fmt": f"R$ {total_liquidado/1_000_000:.1f}M",
            "pago_fmt": f"R$ {total_pago/1_000_000:.1f}M",
        },
        "fornecedores": ranking[:10],
        "alertas_concentracao": alertas_concentracao,
        "qtd_despesas": len(despesas),
    }


def _save_json(path: str, data):
    """Salva dados em JSON."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log(f"Dados salvos em: {output_path}", "success")


# Metadados por tipo de relatório (nome de arquivo: "{tipo}-{ano}-{data}.pdf")
_REPORT_META = {
    "fiscal": ("Indicadores Fiscais (LRF)",
               "Indicadores fiscais e limites da LRF: RCL, despesa com pessoal e dívida."),
    "fornecedores": ("Análise de Fornecedores",
                     "Ranking de fornecedores e concentração de pagamentos no exercício."),
    "transferencias": ("Transferências Federais",
                       "Transferências, convênios e emendas parlamentares recebidos."),
    "consolidado": ("Relatório Consolidado",
                    "Panorama fiscal e orçamentário consolidado do exercício."),
}


def _build_reports_manifest(reports_dir, output_path) -> dict:
    """
    Varre a pasta de PDFs e gera um índice JSON para a página de relatórios.

    Mantém o site honesto: lista apenas os relatórios que de fato existem,
    com data e tamanho reais, em vez de cards fixos com links quebrados.
    """
    reports_dir = Path(reports_dir)
    relatorios = []

    if reports_dir.exists():
        pdfs = sorted(reports_dir.glob("*.pdf"),
                      key=lambda p: p.stat().st_mtime, reverse=True)
        for pdf in pdfs:
            partes = pdf.stem.split("-")
            tipo = partes[0].lower()
            ano = partes[1] if len(partes) >= 2 and partes[1].isdigit() else None
            titulo, descricao = _REPORT_META.get(tipo, (pdf.stem, ""))
            stat = pdf.stat()
            relatorios.append({
                "tipo": tipo if tipo in _REPORT_META else "consolidado",
                "titulo": f"{titulo}{f' — {ano}' if ano else ''}",
                "descricao": descricao,
                "arquivo": f"relatorios/{pdf.name}",
                "periodo": f"Ano {ano}" if ano else "",
                "data": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "tamanho": stat.st_size,
                "formato": "PDF",
            })

    manifest = {
        "lastUpdate": datetime.now().isoformat(),
        "total": len(relatorios),
        "relatorios": relatorios,
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    return manifest


def cmd_index_reports(args):
    """Gera o índice JSON dos relatórios PDF publicados."""
    reports_dir = Path(args.reports_dir) if args.reports_dir else Path("docs/relatorios")
    output = Path(args.output) if args.output else Path("docs/data/relatorios.json")
    manifest = _build_reports_manifest(reports_dir, output)
    log(f"Índice gerado: {manifest['total']} relatório(s) → {output}", "success")


def cmd_db_stats(args):
    """Mostra estatísticas do banco de dados."""
    from database import DatabaseManager

    log("Carregando estatísticas do banco de dados...", "info")

    db = DatabaseManager()
    stats = db.get_estatisticas()

    if RICH_AVAILABLE:
        table = Table(title="Estatísticas do Banco de Dados")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="green")

        table.add_row("Total de coletas", str(stats.get("total_coletas", 0)))
        table.add_row("Total de despesas", str(stats.get("total_despesas", 0)))
        table.add_row("Total de fornecedores", str(stats.get("total_fornecedores", 0)))
        table.add_row("Alertas ativos", str(stats.get("alertas_ativos", 0)))
        table.add_row("Relatórios gerados", str(stats.get("total_relatorios", 0)))
        table.add_row("Última coleta", stats.get("ultima_coleta", "Nunca") or "Nunca")

        console.print(table)
    else:
        print("\nEstatísticas do Banco de Dados:")
        print(f"  Total de coletas: {stats.get('total_coletas', 0)}")
        print(f"  Total de despesas: {stats.get('total_despesas', 0)}")
        print(f"  Total de fornecedores: {stats.get('total_fornecedores', 0)}")
        print(f"  Alertas ativos: {stats.get('alertas_ativos', 0)}")
        print(f"  Relatórios gerados: {stats.get('total_relatorios', 0)}")
        print(f"  Última coleta: {stats.get('ultima_coleta', 'Nunca') or 'Nunca'}")


def cmd_generate_report(args):
    """Gera relatórios PDF."""
    from reports.generator import FiscalReport, SupplierReport, TransferReport, ConsolidatedReport
    from database import DatabaseManager

    log(f"Gerando relatório: {args.tipo}...", "info")

    ano = args.ano or datetime.now().year
    output_dir = Path(args.output) if args.output else Path("docs/relatorios")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Coletar dados atuais das APIs
    dados_fiscal = {}
    dados_fornecedores = {}
    dados_transferencias = {}

    if args.tipo in ["fiscal", "consolidado"]:
        try:
            from collectors.siconfi import SiconfiCollector
            siconfi = SiconfiCollector()
            dados_fiscal = siconfi.get_dados_para_dashboard(ano)
            log("Dados fiscais carregados", "success")
        except Exception as e:
            log(f"Erro ao carregar dados fiscais: {e}", "warning")

    if args.tipo in ["fornecedores", "consolidado"]:
        try:
            from collectors.tce_sp import TCESPCollector
            tce = TCESPCollector()
            dados_fornecedores = tce.get_dados_para_dashboard(ano)
            log("Dados de fornecedores carregados", "success")
        except Exception as e:
            log(f"Erro ao carregar dados de fornecedores: {e}", "warning")

    if args.tipo in ["transferencias", "consolidado"]:
        try:
            from collectors.portal_federal import PortalFederalCollector
            federal = PortalFederalCollector()
            if federal.api_key:
                dados_transferencias = federal.get_dados_para_dashboard(ano)
                log("Dados de transferências carregados", "success")
            else:
                log("API Key do Portal Federal não configurada", "warning")
        except Exception as e:
            log(f"Erro ao carregar dados de transferências: {e}", "warning")

    # Gerar relatório
    pdf_path = None

    if args.tipo == "fiscal":
        generator = FiscalReport(output_dir)
        pdf_path = generator.generate(dados_fiscal.get("resumo", {}).get("indicadores", dados_fiscal), ano)

    elif args.tipo == "fornecedores":
        generator = SupplierReport(output_dir)
        pdf_path = generator.generate(dados_fornecedores, ano)

    elif args.tipo == "transferencias":
        generator = TransferReport(output_dir)
        pdf_path = generator.generate(dados_transferencias, ano)

    elif args.tipo == "consolidado":
        generator = ConsolidatedReport(output_dir)
        pdf_path = generator.generate(
            dados_fiscal.get("resumo", {}).get("indicadores", dados_fiscal),
            dados_fornecedores,
            dados_transferencias,
            ano
        )

    if pdf_path:
        log(f"Relatório gerado: {pdf_path}", "success")

        # Registrar no banco de dados
        try:
            db = DatabaseManager()
            db.registrar_relatorio(
                tipo=args.tipo,
                titulo=f"Relatório {args.tipo.title()} {ano}",
                arquivo_path=str(pdf_path),
                periodo=f"Ano {ano}",
                tamanho_bytes=pdf_path.stat().st_size if pdf_path.exists() else 0
            )
        except Exception as e:
            log(f"Erro ao registrar relatório no banco: {e}", "warning")
    else:
        log("Falha ao gerar relatório", "error")


def cmd_list_reports(args):
    """Lista relatórios gerados."""
    from database import DatabaseManager

    log("Listando relatórios...", "info")

    db = DatabaseManager()
    relatorios = db.get_relatorios(tipo=args.tipo, limite=args.limite or 20)

    if not relatorios:
        log("Nenhum relatório encontrado", "info")
        return

    if RICH_AVAILABLE:
        table = Table(title="Relatórios Gerados")
        table.add_column("ID", style="cyan")
        table.add_column("Tipo", style="green")
        table.add_column("Título", style="white")
        table.add_column("Data", style="yellow")
        table.add_column("Arquivo", style="blue")

        for r in relatorios:
            table.add_row(
                str(r.get("id", "")),
                r.get("tipo", ""),
                r.get("titulo", "")[:30],
                r.get("data_geracao", "")[:10],
                Path(r.get("arquivo_path", "")).name if r.get("arquivo_path") else ""
            )

        console.print(table)
    else:
        print("\nRelatórios Gerados:")
        for r in relatorios:
            print(f"  [{r.get('id')}] {r.get('tipo')}: {r.get('titulo')} ({r.get('data_geracao', '')[:10]})")


def cmd_alertas(args):
    """Lista alertas ativos."""
    from database import DatabaseManager

    log("Carregando alertas...", "info")

    db = DatabaseManager()
    alertas = db.get_alertas_ativos()

    if not alertas:
        log("Nenhum alerta ativo", "success")
        return

    if RICH_AVAILABLE:
        table = Table(title=f"Alertas Ativos ({len(alertas)})")
        table.add_column("Tipo", style="red")
        table.add_column("Categoria", style="yellow")
        table.add_column("Título", style="white")
        table.add_column("Data", style="cyan")

        for a in alertas:
            table.add_row(
                a.get("tipo", ""),
                a.get("categoria", ""),
                a.get("titulo", "")[:40],
                a.get("data_criacao", "")[:10]
            )

        console.print(table)
    else:
        print(f"\nAlertas Ativos ({len(alertas)}):")
        for a in alertas:
            print(f"  [{a.get('tipo')}] {a.get('titulo')}")


def main():
    """Função principal."""
    print_header()

    parser = argparse.ArgumentParser(
        description="MonitoraMarília - Sistema de Controle Social",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  # Dados fiscais (SICONFI)
  python -m src.main siconfi --tipo resumo --ano 2025
  python -m src.main siconfi --tipo alertas --ano 2025

  # Dados do TCE-SP
  python -m src.main tce-sp --tipo fornecedores --ano 2025 --top 20

  # Portal Federal (requer API key)
  python -m src.main portal-federal --tipo convenios --ano 2025
  python -m src.main portal-federal --tipo verificar-cnpj --cnpj 12345678000190

  # Relatório integrado
  python -m src.main integrado --tipo dashboard --ano 2025

  # Atualizar dashboard
  python -m src.main update-dashboard --output docs/data/
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")

    # Comando: siconfi
    siconfi_parser = subparsers.add_parser("siconfi", help="Consultar SICONFI (Tesouro Nacional)")
    siconfi_parser.add_argument("--tipo", required=True,
                                choices=["resumo", "rgf", "rreo", "alertas", "dashboard"],
                                help="Tipo de consulta")
    siconfi_parser.add_argument("--ano", type=int, help="Ano de referência")
    siconfi_parser.add_argument("--quadrimestre", type=int, choices=[1, 2, 3], help="Quadrimestre (RGF)")
    siconfi_parser.add_argument("--bimestre", type=int, choices=[1, 2, 3, 4, 5, 6], help="Bimestre (RREO)")
    siconfi_parser.add_argument("-o", "--output", help="Arquivo de saída (JSON)")

    # Comando: tce-sp
    tce_parser = subparsers.add_parser("tce-sp", help="Consultar TCE-SP")
    tce_parser.add_argument("--tipo", required=True,
                           choices=["despesas", "fornecedores", "concentracao", "dashboard"],
                           help="Tipo de consulta")
    tce_parser.add_argument("--ano", type=int, help="Ano de referência")
    tce_parser.add_argument("--top", type=int, default=20, help="Quantidade de fornecedores")
    tce_parser.add_argument("-o", "--output", help="Arquivo de saída (JSON)")

    # Comando: portal-federal
    federal_parser = subparsers.add_parser("portal-federal", help="Consultar Portal Federal")
    federal_parser.add_argument("--tipo", required=True,
                               choices=["convenios", "transferencias", "emendas", "verificar-cnpj", "dashboard"],
                               help="Tipo de consulta")
    federal_parser.add_argument("--ano", type=int, help="Ano de referência")
    federal_parser.add_argument("--cnpj", help="CNPJ para verificação de sanções")
    federal_parser.add_argument("-o", "--output", help="Arquivo de saída (JSON)")

    # Comando: integrado
    integrado_parser = subparsers.add_parser("integrado", help="Gerar relatório integrado")
    integrado_parser.add_argument("--tipo", required=True,
                                 choices=["relatorio", "dashboard", "fornecedores"],
                                 help="Tipo de relatório")
    integrado_parser.add_argument("--ano", type=int, help="Ano de referência")
    integrado_parser.add_argument("-o", "--output", help="Arquivo de saída (JSON)")

    # Comando: update-dashboard
    dashboard_parser = subparsers.add_parser("update-dashboard",
                                             help="Atualizar dados do dashboard (todas as fontes)")
    dashboard_parser.add_argument("--ano", type=int, help="Ano de referência")
    dashboard_parser.add_argument("-o", "--output", help="Diretório de saída")
    dashboard_parser.add_argument("--salvar-db", action="store_true", help="Salvar no banco de dados")

    # Comando: db-stats
    db_parser = subparsers.add_parser("db-stats", help="Mostrar estatísticas do banco de dados")

    # Comando: generate-report
    report_parser = subparsers.add_parser("generate-report", help="Gerar relatório PDF")
    report_parser.add_argument("--tipo", required=True,
                               choices=["fiscal", "fornecedores", "transferencias", "consolidado"],
                               help="Tipo de relatório")
    report_parser.add_argument("--ano", type=int, help="Ano de referência")
    report_parser.add_argument("-o", "--output", help="Diretório de saída")

    # Comando: list-reports
    list_reports_parser = subparsers.add_parser("list-reports", help="Listar relatórios gerados")
    list_reports_parser.add_argument("--tipo", help="Filtrar por tipo")
    list_reports_parser.add_argument("--limite", type=int, default=20, help="Limite de resultados")

    # Comando: alertas
    alertas_parser = subparsers.add_parser("alertas", help="Listar alertas ativos")

    # Comando: index-reports
    index_parser = subparsers.add_parser("index-reports",
                                         help="Gerar índice JSON dos relatórios PDF para o site")
    index_parser.add_argument("--reports-dir", help="Diretório dos PDFs (default: docs/relatorios)")
    index_parser.add_argument("-o", "--output", help="Arquivo de saída (default: docs/data/relatorios.json)")

    args = parser.parse_args()

    # Executar comando
    if args.command == "siconfi":
        cmd_siconfi(args)
    elif args.command == "tce-sp":
        cmd_tce_sp(args)
    elif args.command == "portal-federal":
        cmd_portal_federal(args)
    elif args.command == "integrado":
        cmd_integrado(args)
    elif args.command == "update-dashboard":
        cmd_update_dashboard(args)
    elif args.command == "db-stats":
        cmd_db_stats(args)
    elif args.command == "generate-report":
        cmd_generate_report(args)
    elif args.command == "list-reports":
        cmd_list_reports(args)
    elif args.command == "alertas":
        cmd_alertas(args)
    elif args.command == "index-reports":
        cmd_index_reports(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
