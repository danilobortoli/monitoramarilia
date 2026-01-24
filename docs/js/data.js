/**
 * MonitoraMarília - Dados do Dashboard
 *
 * Estrutura de dados integrada de múltiplas fontes:
 * - SICONFI (Tesouro Nacional): Dados fiscais, RCL, LRF
 * - TCE-SP: Despesas, receitas, fornecedores
 * - Portal Federal: Transferências, convênios, emendas, sanções
 */

// Dados de exemplo (fallback quando não há JSON atualizado)
const DEFAULT_DATA = {
    lastUpdate: new Date().toISOString(),
    ano: new Date().getFullYear(),
    municipio: "Marília",
    codigoIBGE: "3529005",

    // ========== SICONFI - Dados Fiscais ==========
    fiscal: {
        fonte: "SICONFI - Tesouro Nacional",
        rcl: 850000000,
        rclFormatado: "R$ 850,0M",
        despesaPessoal: {
            valor: 425000000,
            percentual: 50.0,
            limite: 54,
            limiteAlerta: 48.6,
            limitePrudencial: 51.3,
            status: "ok" // ok, alerta, prudencial, critico
        },
        divida: {
            valor: 170000000,
            percentual: 20.0,
            limite: 120,
            status: "ok"
        },
        alertasLRF: []
    },

    // ========== TCE-SP - Execução Orçamentária ==========
    execucao: {
        fonte: "TCE-SP",
        periodo: "Últimos 3 meses",
        empenhado: 125000000,
        empenhadoFmt: "R$ 125,0M",
        liquidado: 118000000,
        liquidadoFmt: "R$ 118,0M",
        pago: 110000000,
        pagoFmt: "R$ 110,0M",
        qtdDespesas: 15420
    },

    // ========== Fornecedores (TCE-SP + Portal Federal) ==========
    fornecedores: {
        fonte: "TCE-SP + Portal Federal",
        totalAnalisados: 100,
        top10: [
            {
                cnpj: "12.345.678/0001-90",
                nome: "DISTRIBUIDORA FARMA LTDA",
                valor: 8500000,
                valorFmt: "R$ 8,50M",
                qtdPagamentos: 45,
                situacaoSancoes: "REGULAR"
            },
            {
                cnpj: "98.765.432/0001-10",
                nome: "CONSTRUTORA ABC S/A",
                valor: 6200000,
                valorFmt: "R$ 6,20M",
                qtdPagamentos: 12,
                situacaoSancoes: "REGULAR"
            },
            {
                cnpj: "11.222.333/0001-44",
                nome: "SERVIÇOS GERAIS ME",
                valor: 4800000,
                valorFmt: "R$ 4,80M",
                qtdPagamentos: 89,
                situacaoSancoes: "REGULAR"
            },
            {
                cnpj: "55.666.777/0001-88",
                nome: "TECNOLOGIA INFO LTDA",
                valor: 3200000,
                valorFmt: "R$ 3,20M",
                qtdPagamentos: 34,
                situacaoSancoes: "REGULAR"
            },
            {
                cnpj: "22.333.444/0001-55",
                nome: "ALIMENTOS E CIA EIRELI",
                valor: 2900000,
                valorFmt: "R$ 2,90M",
                qtdPagamentos: 156,
                situacaoSancoes: "REGULAR"
            }
        ],
        sancoesVerificadas: {
            total: 100,
            regulares: 100,
            irregulares: 0,
            alertas: []
        }
    },

    // ========== Portal Federal - Transferências ==========
    transferencias: {
        fonte: "Portal da Transparência Federal",
        disponivel: true,
        total: 45000000,
        totalFmt: "R$ 45,0M",
        porTipo: {
            "Constitucional": 25000000,
            "Legal": 12000000,
            "Voluntária": 8000000
        }
    },

    // ========== Convênios Federais ==========
    convenios: {
        fonte: "Portal da Transparência Federal",
        quantidade: 12,
        valorTotal: 18500000,
        valorFmt: "R$ 18,5M",
        lista: [
            {
                numero: "890123/2025",
                objeto: "Pavimentação asfáltica",
                valorRepasse: 5200000,
                situacao: "Em Execução",
                orgao: "Ministério das Cidades"
            },
            {
                numero: "890456/2025",
                objeto: "Equipamentos de saúde",
                valorRepasse: 3800000,
                situacao: "Em Execução",
                orgao: "Ministério da Saúde"
            }
        ]
    },

    // ========== Emendas Parlamentares ==========
    emendas: {
        fonte: "Portal da Transparência Federal",
        quantidade: 8,
        valorTotal: 12000000,
        valorFmt: "R$ 12,0M",
        porAutor: [
            { autor: "Dep. Federal A", valor: 4500000, quantidade: 3 },
            { autor: "Dep. Federal B", valor: 3200000, quantidade: 2 },
            { autor: "Sen. Federal C", valor: 4300000, quantidade: 3 }
        ]
    },

    // ========== Alertas Consolidados ==========
    alertas: {
        total: 5,
        lrf: [],
        fornecedores: [],
        outros: [
            {
                tipo: "info",
                categoria: "fiscal",
                titulo: "Despesa com pessoal dentro do limite",
                descricao: "Percentual de 50,0% está abaixo do limite de alerta (48,6%)",
                data: new Date().toISOString().split('T')[0]
            }
        ]
    },

    // ========== Gráficos ==========
    graficos: {
        despesasPorOrgao: {
            labels: ["Saúde", "Educação", "Administração", "Obras", "Assistência Social", "Outros"],
            valores: [35, 28, 15, 10, 7, 5]
        },
        evolucaoMensal: {
            labels: ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"],
            empenhado: [35.2, 32.1, 38.5, 36.8, 34.2, 37.9, 35.6, 33.8, 36.2, 38.1, 35.4, 42.3],
            liquidado: [33.1, 30.5, 36.2, 35.1, 32.8, 35.6, 34.2, 32.1, 34.8, 36.5, 33.9, 40.1],
            pago: [31.5, 29.8, 34.8, 33.9, 31.2, 34.2, 32.8, 30.9, 33.2, 35.1, 32.5, 38.5]
        }
    },

    // ========== Metadados das Fontes ==========
    fontes: {
        siconfi: {
            nome: "SICONFI - Tesouro Nacional",
            url: "https://siconfi.tesouro.gov.br",
            dados: ["RGF", "RREO", "DCA"],
            atualizacao: "Quadrimestral/Bimestral"
        },
        tceSP: {
            nome: "TCE-SP - Tribunal de Contas SP",
            url: "https://transparencia.tce.sp.gov.br",
            dados: ["Despesas", "Receitas"],
            atualizacao: "Mensal"
        },
        portalFederal: {
            nome: "Portal da Transparência Federal",
            url: "https://portaldatransparencia.gov.br",
            dados: ["Convênios", "Transferências", "CEIS", "CNEP", "Emendas"],
            requerApiKey: true,
            atualizacao: "Diária"
        }
    }
};

// Inicializar com dados padrão
let DASHBOARD_DATA = { ...DEFAULT_DATA };

// Tentar carregar dados atualizados do JSON
(async function loadData() {
    try {
        const response = await fetch('data/dashboard.json');
        if (response.ok) {
            const data = await response.json();
            DASHBOARD_DATA = { ...DEFAULT_DATA, ...data };
            console.log('✓ Dados atualizados carregados:', DASHBOARD_DATA.lastUpdate);

            // Re-inicializar dashboard se já carregado
            if (typeof initDashboard === 'function') {
                initDashboard();
            }
        }
    } catch (e) {
        console.log('Usando dados de exemplo (desenvolvimento)');
    }
    window.DASHBOARD_DATA = DASHBOARD_DATA;
})();

// Disponibilizar globalmente
window.DASHBOARD_DATA = DASHBOARD_DATA;
