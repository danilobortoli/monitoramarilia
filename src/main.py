#!/usr/bin/env python3
"""
MonitoraMarília - CLI Principal
Sistema de monitoramento do Portal de Transparência de Marília.

Desenvolvido pela MATRA - Marília Transparente
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Importar coletores
from collectors.licitacoes import LicitacoesCollector
from collectors.despesas import DespesasCollector
from collectors.contratos import ContratosCollector

# Importar analisadores
from analyzers.lai_compliance import LAIComplianceAnalyzer
from analyzers.anomaly_detector import AnomalyDetector


def print_header():
    """Imprime o cabeçalho do sistema."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║              MonitoraMarília - Controle Social               ║
║                  MATRA - Marília Transparente                ║
╚══════════════════════════════════════════════════════════════╝
    """)


def cmd_check_lai(args):
    """Verifica conformidade com a LAI."""
    print("\n[LAI] Verificando conformidade com a Lei de Acesso à Informação...\n")

    analyzer = LAIComplianceAnalyzer()
    report = analyzer.run_compliance_check()

    # Mostrar resumo
    resumo = report["resumo"]
    print(f"Resultado: {resumo['score']} de conformidade")
    print(f"  - Conformes: {resumo['conformes']}/{resumo['total_itens']}")
    print(f"  - Atenção: {resumo['atencao']}")
    print(f"  - Irregulares: {resumo['irregulares']}")

    # Mostrar itens
    print("\nDetalhamento:")
    for item in report["itens"]:
        status_icon = "✓" if item["status"] == "ok" else "!" if item["status"] == "warning" else "✗"
        print(f"  [{status_icon}] {item['item']}: {item['observacao']}")

    # Exportar se solicitado
    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nRelatório salvo em: {output_path}")

    # Atualizar dados do dashboard
    if args.update_dashboard:
        dashboard_data = analyzer.get_summary_for_dashboard()
        dashboard_path = Path("docs/data/lai-compliance.json")
        dashboard_path.parent.mkdir(parents=True, exist_ok=True)
        with open(dashboard_path, "w", encoding="utf-8") as f:
            json.dump(dashboard_data, f, ensure_ascii=False, indent=2)
        print(f"Dashboard atualizado: {dashboard_path}")


def cmd_collect(args):
    """Coleta dados do portal."""
    print(f"\n[COLETA] Coletando dados de {args.type}...\n")

    ano = args.ano or datetime.now().year

    if args.type == "licitacoes":
        collector = LicitacoesCollector()
        data = collector.collect(ano=ano)
    elif args.type == "despesas":
        collector = DespesasCollector()
        data = collector.collect(ano=ano, mes=args.mes)
    elif args.type == "contratos":
        collector = ContratosCollector()
        data = collector.collect(ano=ano)
    else:
        print(f"Tipo desconhecido: {args.type}")
        return

    print(f"Coletados {len(data)} registros")

    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Dados salvos em: {output_path}")


def cmd_analyze(args):
    """Analisa dados em busca de anomalias."""
    print(f"\n[ANÁLISE] Analisando dados...\n")

    detector = AnomalyDetector()

    # Carregar dados se fornecidos
    despesas = []
    contratos = []
    licitacoes = []

    if args.despesas_file:
        with open(args.despesas_file, "r", encoding="utf-8") as f:
            despesas = json.load(f)

    if args.contratos_file:
        with open(args.contratos_file, "r", encoding="utf-8") as f:
            contratos = json.load(f)

    if args.licitacoes_file:
        with open(args.licitacoes_file, "r", encoding="utf-8") as f:
            licitacoes = json.load(f)

    # Executar análise
    report = detector.run_full_analysis(
        despesas=despesas,
        contratos=contratos,
        licitacoes=licitacoes
    )

    # Mostrar resumo
    print(f"Total de alertas: {report['total_alertas']}")
    print(f"  - Críticos: {report['criticos']}")
    print(f"  - Alertas: {report['alertas']}")
    print(f"  - Informativos: {report['info']}")

    if report['detalhes']:
        print("\nAlertas detectados:")
        for alerta in report['detalhes']:
            tipo_icon = "🔴" if alerta['tipo'] == 'critico' else "🟡" if alerta['tipo'] == 'alerta' else "🔵"
            print(f"\n  {tipo_icon} {alerta['titulo']}")
            print(f"     {alerta['descricao'][:100]}...")

    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\nRelatório salvo em: {output_path}")


def cmd_update_dashboard(args):
    """Atualiza os dados do dashboard."""
    print("\n[DASHBOARD] Atualizando dados do dashboard...\n")

    ano = args.ano or datetime.now().year
    docs_data = Path("docs/data")
    docs_data.mkdir(parents=True, exist_ok=True)

    # 1. Verificar LAI
    print("1. Verificando conformidade LAI...")
    lai_analyzer = LAIComplianceAnalyzer()
    lai_report = lai_analyzer.run_compliance_check()
    lai_dashboard = lai_analyzer.get_summary_for_dashboard()

    with open(docs_data / "lai-compliance.json", "w", encoding="utf-8") as f:
        json.dump(lai_dashboard, f, ensure_ascii=False, indent=2)

    # 2. Coletar dados
    print("2. Coletando licitações...")
    lic_collector = LicitacoesCollector()
    licitacoes = lic_collector.collect(ano=ano)

    print("3. Coletando contratos...")
    cont_collector = ContratosCollector()
    contratos = cont_collector.collect(ano=ano)

    print("4. Coletando despesas...")
    desp_collector = DespesasCollector()
    despesas = desp_collector.collect(ano=ano)

    # 3. Analisar anomalias
    print("5. Analisando anomalias...")
    detector = AnomalyDetector()
    anomalias = detector.run_full_analysis(
        despesas=despesas,
        contratos=contratos,
        licitacoes=licitacoes
    )

    with open(docs_data / "alertas.json", "w", encoding="utf-8") as f:
        json.dump(detector.get_alerts_for_dashboard(), f, ensure_ascii=False, indent=2)

    # 4. Salvar dados
    with open(docs_data / "licitacoes.json", "w", encoding="utf-8") as f:
        json.dump(licitacoes[:20], f, ensure_ascii=False, indent=2)  # Top 20

    # 5. Gerar dados consolidados para o dashboard
    dashboard_data = {
        "lastUpdate": datetime.now().isoformat(),
        "kpis": {
            "laiScore": lai_dashboard["laiScore"],
            "laiItems": lai_dashboard["laiItems"],
            "laiCompliant": lai_dashboard["laiCompliant"],
            "licitacoesCount": len(licitacoes),
            "licitacoesValor": f"{sum(l.get('valor_homologado', 0) for l in licitacoes):,.2f}",
            "contratosCount": len([c for c in contratos if c.get('status', '').lower() == 'vigente']),
            "contratosAditivos": len([c for c in contratos if c.get('qtd_aditivos', 0) > 0]),
            "alertasCount": anomalias["total_alertas"],
            "alertasCriticos": anomalias["criticos"]
        },
        "laiChecklist": lai_dashboard["checklist"],
        "alertas": detector.get_alerts_for_dashboard()[:10],
        "licitacoes": licitacoes[:5]
    }

    with open(docs_data / "dashboard.json", "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)

    print("\n✓ Dashboard atualizado com sucesso!")
    print(f"  Arquivos gerados em: {docs_data}")


def main():
    """Função principal."""
    print_header()

    parser = argparse.ArgumentParser(
        description="MonitoraMarília - Sistema de Controle Social"
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")

    # Comando: check-lai
    lai_parser = subparsers.add_parser("check-lai", help="Verificar conformidade LAI")
    lai_parser.add_argument("-o", "--output", help="Arquivo de saída (JSON)")
    lai_parser.add_argument("--update-dashboard", action="store_true",
                           help="Atualizar dados do dashboard")

    # Comando: collect
    collect_parser = subparsers.add_parser("collect", help="Coletar dados do portal")
    collect_parser.add_argument("--type", required=True,
                               choices=["licitacoes", "despesas", "contratos"],
                               help="Tipo de dados")
    collect_parser.add_argument("--ano", type=int, help="Ano de referência")
    collect_parser.add_argument("--mes", type=int, help="Mês (apenas despesas)")
    collect_parser.add_argument("-o", "--output", help="Arquivo de saída (JSON)")

    # Comando: analyze
    analyze_parser = subparsers.add_parser("analyze", help="Analisar dados")
    analyze_parser.add_argument("--despesas-file", help="Arquivo JSON de despesas")
    analyze_parser.add_argument("--contratos-file", help="Arquivo JSON de contratos")
    analyze_parser.add_argument("--licitacoes-file", help="Arquivo JSON de licitações")
    analyze_parser.add_argument("-o", "--output", help="Arquivo de saída (JSON)")

    # Comando: update-dashboard
    dashboard_parser = subparsers.add_parser("update-dashboard",
                                             help="Atualizar dados do dashboard")
    dashboard_parser.add_argument("--ano", type=int, help="Ano de referência")

    args = parser.parse_args()

    if args.command == "check-lai":
        cmd_check_lai(args)
    elif args.command == "collect":
        cmd_collect(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "update-dashboard":
        cmd_update_dashboard(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
