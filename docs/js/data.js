/**
 * MonitoraMarília - Dados do Dashboard
 *
 * IMPORTANTE: Este arquivo contém apenas a estrutura de dados.
 * Os dados reais devem ser carregados de docs/data/dashboard.json,
 * gerado pelo comando: python -m src.main update-dashboard
 *
 * Fontes de dados:
 * - SICONFI (Tesouro Nacional): Dados fiscais, RCL, LRF
 * - TCE-SP: Despesas, receitas, fornecedores
 * - Portal Federal: Transferências, convênios, emendas, sanções
 */

// Estrutura vazia (placeholder) - dados reais vêm do JSON
const DEFAULT_DATA = {
    lastUpdate: null,
    ano: new Date().getFullYear(),
    municipio: "Marília",
    codigoIBGE: "3529005",
    dadosCarregados: false, // Flag para indicar se dados reais foram carregados

    // ========== SICONFI - Dados Fiscais ==========
    fiscal: {
        fonte: "SICONFI - Tesouro Nacional",
        rcl: null,
        rclFormatado: null,
        despesaPessoal: {
            valor: null,
            percentual: null,
            limite: 54,
            limiteAlerta: 48.6,
            limitePrudencial: 51.3,
            status: null
        },
        divida: {
            valor: null,
            percentual: null,
            limite: 120,
            status: null
        },
        alertasLRF: []
    },

    // ========== TCE-SP - Execução Orçamentária ==========
    execucao: {
        fonte: "TCE-SP",
        periodo: null,
        empenhado: null,
        empenhadoFmt: null,
        liquidado: null,
        liquidadoFmt: null,
        pago: null,
        pagoFmt: null,
        qtdDespesas: null
    },

    // ========== Fornecedores (TCE-SP + Portal Federal) ==========
    fornecedores: {
        fonte: "TCE-SP + Portal Federal",
        totalAnalisados: 0,
        top10: [],
        sancoesVerificadas: {
            total: 0,
            regulares: 0,
            irregulares: 0,
            alertas: []
        }
    },

    // ========== Portal Federal - Transferências ==========
    transferencias: {
        fonte: "Portal da Transparência Federal",
        disponivel: false,
        total: null,
        totalFmt: null,
        porTipo: {}
    },

    // ========== Convênios Federais ==========
    convenios: {
        fonte: "Portal da Transparência Federal",
        quantidade: null,
        valorTotal: null,
        valorFmt: null,
        lista: []
    },

    // ========== Emendas Parlamentares ==========
    emendas: {
        fonte: "Portal da Transparência Federal",
        quantidade: null,
        valorTotal: null,
        valorFmt: null,
        porAutor: []
    },

    // ========== Alertas Consolidados ==========
    alertas: {
        total: 0,
        lrf: [],
        fornecedores: [],
        outros: []
    },

    // ========== Gráficos ==========
    graficos: {
        despesasPorOrgao: {
            labels: [],
            valores: []
        },
        evolucaoMensal: {
            labels: [],
            empenhado: [],
            liquidado: [],
            pago: []
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
            DASHBOARD_DATA = { ...DEFAULT_DATA, ...data, dadosCarregados: true };
            console.log('✓ Dados atualizados carregados:', DASHBOARD_DATA.lastUpdate);

            // Re-inicializar dashboard se já carregado
            if (typeof initDashboard === 'function') {
                initDashboard();
            }
        } else {
            console.warn('⚠ Arquivo dashboard.json não encontrado. Execute: python -m src.main update-dashboard');
        }
    } catch (e) {
        console.warn('⚠ Dados não carregados. Execute: python -m src.main update-dashboard');
    }
    window.DASHBOARD_DATA = DASHBOARD_DATA;
})();

// Disponibilizar globalmente
window.DASHBOARD_DATA = DASHBOARD_DATA;
