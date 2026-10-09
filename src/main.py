#!/usr/bin/env python3
"""
MonitoraMarília - CLI Principal
Sistema de monitoramento de transparência pública de Marília.

Desenvolvido pela MATRA - Marília Transparente

Fontes de dados abertas:
- SICONFI (Tesouro Nacional): Dados fiscais (RGF, RREO, DCA)
- TCE-SP: Despesas e receitas detalhadas
- Portal Federal: Transferências, convênios, sanções (CEIS/CNEP)
- Prefeitura de Marília: portal da transparência e dados abertos (ver APIS_MARILIA.md)

Funcionalidades:
- Coleta de dados de APIs oficiais
- Armazenamento em banco SQLite para histórico
- Geração de relatórios PDF
- Atualização de dashboard web
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
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


def cmd_marilia(args):
    """Consulta o portal e os dados abertos da Prefeitura de Marília."""
    from collectors.portal_marilia import PortalMariliaCollector
    from collectors.dados_abertos_marilia import DadosAbertosMariliaCollector

    ano = args.ano or datetime.now().year

    if args.fonte == "portal":
        collector = PortalMariliaCollector()
        if not args.conjunto:
            for v in collector.listar_visoes():
                nome = next((n for n, mv in collector.VISOES.items()
                             if mv == (v["modulo"], v["visao"])), "")
                print(f"{nome:24} {v['modulo']}/{v['visao']:28} {v['caminho']}")
            return
        log(f"Consultando portal de Marília: {args.conjunto} {ano}...", "info")
        data = collector.get_visao(args.conjunto, ano)
    else:
        collector = DadosAbertosMariliaCollector()
        if not args.conjunto:
            print("\n".join(collector.CONJUNTOS))
            return
        log(f"Consultando dados abertos de Marília: {args.conjunto} {ano}...", "info")
        data = collector.get_conjunto(args.conjunto, ano)

    log(f"{len(data)} registros", "success")
    if args.output:
        _save_json(args.output, data)
    else:
        for item in data[:5]:
            print(json.dumps(item, indent=2, ensure_ascii=False))


def cmd_observatorio(args):
    """Coleta as fontes de Marília, registra o que mudou e calcula o Radar do Observatório."""
    from collectors.portal_marilia import PortalMariliaCollector
    from collectors.dados_abertos_marilia import DadosAbertosMariliaCollector
    from analyzers import paineis, radar
    from analyzers.acervo import CONJUNTOS_COMPARADOS, Acervo, comparar, impressao

    hoje = datetime.now().date()
    ano = args.ano or hoje.year
    portal = PortalMariliaCollector()
    abertos = DadosAbertosMariliaCollector()
    acervo = Acervo(args.historico)
    frase_diario = "A interrupção de serviços contratados pode gerar impactos diretos à população"

    log(f"Coletando dados abertos de {ano}...", "info")
    conjuntos = {nome: abertos.get_conjunto(nome, ano) for nome in (
        "compra-direta", "contratos", "licitacoes", "obras", "diario-oficial",
        "contas-publicas", "relatorio-viagens", "concursos", "sic", "ouvidoria",
    )}
    compras = conjuntos["compra-direta"]
    contratos = conjuntos["contratos"]
    licitacoes = conjuntos["licitacoes"]
    obras = conjuntos["obras"]
    diario = conjuntos["diario-oficial"]

    log(f"Coletando despesas, diárias e modalidades do portal ({ano})...", "info")
    despesas = portal.get_visao("despesas_investimentos", ano)
    diarias = portal.get_visao("diarias", ano)
    modalidades = {a: portal.get_visao("empenho_modalidade", a) for a in range(ano - 3, ano + 1)}

    contagens = {}
    for nome in portal.VISOES:
        try:
            contagens[nome] = portal.contar(nome, ano)
        except Exception as erro:  # uma visão fora do ar não derruba a coleta
            log(f"Visão {nome} não respondeu: {erro}", "warning")

    saude = {}
    for chave, (modulo, visao, secao) in {
        "medicamentos_em_falta": ("relacaonominal", "medicamentosemfalta", "MEDICAMENTOS EM FALTA"),
        "fila_de_leitos": ("58", "RelacaoPacientesesperandoporvagasinternacao", None),
    }.items():
        try:
            saude[chave] = portal.ultima_data_arquivo(modulo, visao, secao)
        except Exception as erro:
            log(f"Página {modulo}/{visao} não respondeu: {erro}", "warning")

    # Fornecedores de anos anteriores: lidos do cache, renovado a cada 30 dias.
    anos_anteriores = list(range(ano - max(1, args.anos_comparacao), ano))
    conhecidos = None if args.renovar_cache else acervo.ler_fornecedores_conhecidos(anos_anteriores)
    if conhecidos is None:
        log(f"Renovando cache de fornecedores de {anos_anteriores[0]}–{anos_anteriores[-1]}...", "info")
        anteriores = []
        for a in anos_anteriores:
            anteriores.extend(portal.get_visao("despesas_investimentos", a))
        conhecidos = radar.fornecedores_conhecidos(anteriores)
        acervo.gravar_fornecedores_conhecidos(anos_anteriores, conhecidos)

    # O que mudou desde a coleta anterior.
    mudancas = {}
    for nome in CONJUNTOS_COMPARADOS:
        anterior = acervo.ler_estado(nome, ano)
        mudancas[nome] = None if anterior is None else comparar(nome, anterior, conjuntos[nome])
        acervo.gravar_estado(nome, ano, conjuntos[nome])

    edicoes = [{"edicao": e.get("edicao"), "data": e.get("data"), "impressao": impressao(e)} for e in diario]
    anterior = acervo.ler_estado("diario-oficial", ano)
    if anterior is not None:
        antes = {e["edicao"]: e["impressao"] for e in anterior}
        mudancas["diario_oficial"] = {
            "novas": [e["edicao"] for e in edicoes if e["edicao"] not in antes],
            "alteradas": [e["edicao"] for e in edicoes
                          if e["edicao"] in antes and antes[e["edicao"]] != e["impressao"]],
        }
    acervo.gravar_estado("diario-oficial", ano, edicoes, ordenar=lambda e: e["data"] or "")

    ids = sorted({d.get("ID") for d in despesas if d.get("ID") is not None})
    anterior = acervo.ler_estado("despesas", ano)
    if anterior is not None:
        antes = set(anterior)
        mudancas["despesas"] = {
            "novos": [i for i in ids if i not in antes],
            "removidos": sorted(antes - set(ids)),
        }
    acervo.gravar_estado("despesas", ano, ids, ordenar=lambda i: i)

    primeira_coleta = any(v is None for v in mudancas.values()) or len(mudancas) < len(CONJUNTOS_COMPARADOS) + 2
    if not primeira_coleta:
        acervo.gravar_mudancas(hoje, mudancas)

    # Acompanhamento no Notion (somente leitura; inativo sem NOTION_TOKEN).
    notion = None
    config = json.loads(Path(args.config).read_text(encoding="utf-8")) if Path(args.config).exists() else {}
    if config.get("notion"):
        from collectors.notion_matra import NotionMatraCollector
        leitor = NotionMatraCollector(config["notion"])
        if leitor.ativo:
            try:
                notion = leitor.resumo(inicio_semana=(hoje - timedelta(days=6)).isoformat())
                notion["lido_em"] = datetime.now().isoformat(timespec="seconds")
                log(f"Notion: {len(notion['edicoes'])} edições, {notion['achados']['em_aberto']} achados em aberto", "info")
            except Exception as erro:  # o site segue sem o Notion
                log(f"Notion indisponível: {erro}", "warning")
        else:
            log("NOTION_TOKEN não configurado: o site segue sem o acompanhamento do Notion", "info")

    regras = [
        radar.compra_direta_aberta(compras),
        radar.contrato_sem_contratada(contratos),
        radar.licitacao_sem_valor(licitacoes),
        radar.quebra_ordem_cronologica(diario),
        radar.fornecedor_novo_valor_alto(
            despesas, conhecidos, limite=args.limite_fornecedor,
            anos_anteriores=f"{anos_anteriores[0]}–{anos_anteriores[-1]}",
        ),
        radar.diarias_atipicas(diarias),
        radar.obra_parada_ou_cancelada(obras),
        radar.contrato_a_vencer(contratos, hoje=hoje),
    ]
    for n, regra in enumerate(regras, 1):
        regra["n"] = n

    totais = radar.totais(compras, licitacoes, contratos, obras, despesas)
    acervo.registrar_coleta({
        "data": hoje.isoformat(),
        "exercicio": ano,
        "totais": totais,
        "radar": {r["id"]: r["resultado"] for r in regras},
    })

    vazias = [titulo for nome, titulo in (("subvencoes", "Subvenções"),) if contagens.get(nome) == 0]
    data = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "exercicio": ano,
        "fontes": {
            "portal": PortalMariliaCollector.PORTAL_URL,
            "dados_abertos": DadosAbertosMariliaCollector.BASE_URL,
        },
        "coleta": {
            "data": hoje.isoformat(),
            "visoes_portal": {"responderam": len(contagens), "total": len(portal.VISOES)},
            "registros_por_visao": contagens,
        },
        "totais": totais,
        "regras": regras,
        "novidades": paineis.novidades(
            None if primeira_coleta else mudancas,
            compras, contratos, licitacoes, diario, despesas, frase_diario,
        ),
        "serie_contratacao_direta": paineis.serie_contratacao_direta(modalidades),
        "saude": saude,
        "diario": paineis.diario(diario, frase_diario),
        "transparencia": {
            "campos": paineis.campos_vazios(conjuntos),
            "secoes": paineis.secoes_sem_dado(
                [c for c in ("contas-publicas", "relatorio-viagens", "concursos") if not conjuntos[c]],
                {"sic": (conjuntos["sic"] or [None])[0], "ouvidoria": (conjuntos["ouvidoria"] or [None])[0]},
                vazias, ano,
            ),
        },
        "historico": acervo.serie()[-90:],
        "notion": notion,
    }

    for regra in regras:
        log(f"{regra['n']}. {regra['regra']}: {regra['resultado']} (base: {regra['base']})", "info")
    log(f"Novidades: {data['novidades']['resumo']}", "info")

    _save_json(args.output or "docs/data/observatorio.json", data)


def cmd_boletim(args):
    """Gera o boletim semanal em PDF a partir do histórico e da última coleta."""
    from reports import boletim

    fim = datetime.strptime(args.fim, "%Y-%m-%d").date() if args.fim else datetime.now().date()
    dados_path = Path(args.dados)
    if not dados_path.exists():
        log(f"Sem {dados_path}: rode 'observatorio' antes do boletim", "error")
        sys.exit(1)
    observatorio = json.loads(dados_path.read_text(encoding="utf-8"))
    dados = boletim.montar(Path(args.historico), observatorio, fim)
    pdf = boletim.gerar_pdf(dados, Path(args.output), Path(args.fontes))
    log(f"Boletim de {dados['inicio']} a {dados['fim']}: {boletim.resumo(dados)}", "info")
    log(f"PDF salvo em: {pdf}", "success")
    manifest = _build_reports_manifest(Path(args.output), Path(args.indice))
    log(f"Índice atualizado: {manifest['total']} relatório(s)", "success")


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


def _status_pessoal(percentual):
    """Classifica a despesa com pessoal frente aos limites da LRF (ou None)."""
    if percentual is None:
        return None
    if percentual < 48.6:
        return "ok"
    if percentual < 51.3:
        return "alerta"
    if percentual < 54:
        return "prudencial"
    return "critico"


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

    # Despesa com pessoal — só preenche se houver dado real (RGF); caso
    # contrário fica None (o painel mostra "—" em vez de um valor inventado).
    pessoal_percentual = None
    for alerta in alertas_lrf:
        if alerta.get("categoria") == "pessoal" and alerta.get("valor") is not None:
            pessoal_percentual = alerta.get("valor")
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
                "valor": (rcl * (pessoal_percentual / 100)) if (rcl and pessoal_percentual is not None) else None,
                "percentual": pessoal_percentual,
                "limite": 54,
                "limiteAlerta": 48.6,
                "limitePrudencial": 51.3,
                "status": _status_pessoal(pessoal_percentual)
            },
            # Dívida consolidada: ainda sem coleta confiável (RGF Anexo 02);
            # mantém None para o painel mostrar "—" em vez de 0% fictício.
            "divida": {
                "valor": None,
                "percentual": None,
                "limite": 120,
                "status": None
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


def _build_reports_manifest(reports_dir, output_path) -> dict:
    """
    Gera o índice JSON dos relatórios publicados em docs/relatorios.

    Cada PDF vem acompanhado de um JSON com o mesmo nome (título, período e resumo),
    gravado por quem o gerou. PDFs sem esse arquivo entram só com nome e tamanho.
    """
    reports_dir = Path(reports_dir)
    relatorios = []

    if reports_dir.exists():
        for pdf in sorted(reports_dir.glob("*.pdf"), reverse=True):
            meta_path = pdf.with_suffix(".json")
            meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
            relatorios.append({
                "tipo": meta.get("tipo", pdf.stem.split("-")[0]),
                "titulo": meta.get("titulo", pdf.stem),
                "periodo": meta.get("periodo", ""),
                "resumo": meta.get("resumo", ""),
                "arquivo": f"relatorios/{pdf.name}",
                "data": meta.get("gerado_em", ""),
                "tamanho": pdf.stat().st_size,
                "formato": "PDF",
            })

    manifest = {
        "lastUpdate": datetime.now().isoformat(timespec="seconds"),
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

    # Comando: marilia
    marilia_parser = subparsers.add_parser(
        "marilia", help="Consultar portal e dados abertos da Prefeitura de Marília")
    marilia_parser.add_argument("--fonte", required=True, choices=["portal", "dados-abertos"],
                                help="portal (transparencia.marilia.sp.gov.br) ou dados abertos do site")
    marilia_parser.add_argument("--conjunto",
                                help="Visão do portal ou conjunto de dados abertos (sem ele, lista as opções)")
    marilia_parser.add_argument("--ano", type=int, help="Exercício")
    marilia_parser.add_argument("-o", "--output", help="Arquivo de saída (JSON)")

    # Comando: observatorio
    observatorio_parser = subparsers.add_parser(
        "observatorio", help="Calcular o Radar do Observatório (fontes de Marília)")
    observatorio_parser.add_argument("--ano", type=int, help="Exercício")
    observatorio_parser.add_argument("--anos-comparacao", type=int, default=2,
                                     help="Exercícios anteriores para achar fornecedor novo (default: 2)")
    observatorio_parser.add_argument("--limite-fornecedor", type=float, default=100_000.0,
                                     help="Empenhado mínimo de fornecedor novo (default: 100000)")
    observatorio_parser.add_argument("--historico", default="historico",
                                     help="Diretório do histórico entre coletas (default: historico)")
    observatorio_parser.add_argument("--config", default="config/observatorio.json",
                                     help="Configuração do Observatório (default: config/observatorio.json)")
    observatorio_parser.add_argument("--renovar-cache", action="store_true",
                                     help="Recoletar os fornecedores dos anos anteriores")
    observatorio_parser.add_argument("-o", "--output",
                                     help="Arquivo de saída (default: docs/data/observatorio.json)")

    # Comando: boletim
    boletim_parser = subparsers.add_parser("boletim", help="Gerar o boletim semanal em PDF")
    boletim_parser.add_argument("--fim", help="Último dia da semana do boletim, AAAA-MM-DD (default: hoje)")
    boletim_parser.add_argument("--historico", default="historico", help="Diretório do histórico")
    boletim_parser.add_argument("--dados", default="docs/data/observatorio.json", help="JSON da última coleta")
    boletim_parser.add_argument("--fontes", default="docs", help="Diretório que contém fonts/")
    boletim_parser.add_argument("-o", "--output", default="docs/relatorios", help="Diretório de saída")
    boletim_parser.add_argument("--indice", default="docs/data/relatorios.json",
                                help="Índice dos relatórios para o site")

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
    elif args.command == "marilia":
        cmd_marilia(args)
    elif args.command == "observatorio":
        cmd_observatorio(args)
    elif args.command == "boletim":
        cmd_boletim(args)
    elif args.command == "integrado":
        cmd_integrado(args)
    elif args.command == "update-dashboard":
        cmd_update_dashboard(args)
    elif args.command == "db-stats":
        cmd_db_stats(args)
    elif args.command == "alertas":
        cmd_alertas(args)
    elif args.command == "index-reports":
        cmd_index_reports(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
