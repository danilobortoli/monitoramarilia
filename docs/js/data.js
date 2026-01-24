/**
 * MonitoraMarília - Dados do Dashboard
 *
 * Carrega dados do JSON gerado pelo GitHub Actions.
 * Se não disponível, usa dados de exemplo como fallback.
 */

// Dados de exemplo (fallback quando não há JSON atualizado)
const DEFAULT_DATA = {
    lastUpdate: new Date().toISOString(),
    kpis: {
        laiScore: "87%",
        laiItems: 12,
        laiCompliant: 10,
        licitacoesCount: 156,
        licitacoesValor: "45.230.000,00",
        contratosCount: 89,
        contratosAditivos: 23,
        alertasCount: 7,
        alertasCriticos: 2
    },
    laiChecklist: [
        { id: 1, item: "Estrutura organizacional", status: "ok", url: "https://transparencia.marilia.sp.gov.br/#/estrutura" },
        { id: 2, item: "Competências e atribuições", status: "ok", url: "https://transparencia.marilia.sp.gov.br/#/competencias" },
        { id: 3, item: "Endereços e telefones", status: "ok", url: "https://transparencia.marilia.sp.gov.br/#/contato" },
        { id: 4, item: "Horários de atendimento", status: "ok", url: "https://transparencia.marilia.sp.gov.br/#/atendimento" },
        { id: 5, item: "Repasses e transferências", status: "ok", url: "https://transparencia.marilia.sp.gov.br/#/repasses" },
        { id: 6, item: "Despesas (execução orçamentária)", status: "ok", url: "https://transparencia.marilia.sp.gov.br/#/despesas" },
        { id: 7, item: "Licitações e contratos", status: "ok", url: "https://transparencia.marilia.sp.gov.br/#/licitacoes" },
        { id: 8, item: "Receitas", status: "ok", url: "https://transparencia.marilia.sp.gov.br/#/receitas" },
        { id: 9, item: "Perguntas frequentes", status: "warning", url: null, note: "Seção incompleta" },
        { id: 10, item: "Ferramenta de pesquisa", status: "ok", url: "https://transparencia.marilia.sp.gov.br/#/pesquisa" },
        { id: 11, item: "Dados em formatos abertos", status: "warning", url: null, note: "Apenas PDF disponível" },
        { id: 12, item: "Relatório estatístico LAI", status: "ok", url: "https://transparencia.marilia.sp.gov.br/#/relatorio-lai" }
    ],
    alertas: [
        { id: 1, tipo: "critico", titulo: "Contrato sem licitação - valor elevado", descricao: "Contrato nº 2026/089 no valor de R$ 890.000,00 firmado por dispensa de licitação.", data: "2026-01-15", categoria: "contratos" },
        { id: 2, tipo: "critico", titulo: "Possível fracionamento de despesas", descricao: "Detectadas 5 compras de material de escritório no mesmo mês, totalizando R$ 78.000,00.", data: "2026-01-12", categoria: "despesas" },
        { id: 3, tipo: "alerta", titulo: "Atraso na atualização de despesas", descricao: "Dados de despesas não atualizados há 3 dias.", data: "2026-01-18", categoria: "lai" },
        { id: 4, tipo: "alerta", titulo: "Fornecedor com alta concentração", descricao: "Empresa XYZ LTDA recebeu 15% do total de pagamentos.", data: "2026-01-10", categoria: "fornecedores" },
        { id: 5, tipo: "info", titulo: "Aditivo contratual acima de 25%", descricao: "Contrato nº 2025/045 teve aditivo de 32%.", data: "2026-01-08", categoria: "contratos" }
    ],
    despesasPorCategoria: {
        labels: ["Pessoal", "Custeio", "Investimentos", "Saúde", "Educação", "Outros"],
        data: [45, 20, 10, 12, 8, 5],
        valores: ["R$ 180M", "R$ 80M", "R$ 40M", "R$ 48M", "R$ 32M", "R$ 20M"]
    },
    despesasMensais: {
        labels: ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"],
        empenhado: [35.2, 32.1, 38.5, 36.8, 34.2, 37.9, 35.6, 33.8, 36.2, 38.1, 35.4, 42.3],
        liquidado: [33.1, 30.5, 36.2, 35.1, 32.8, 35.6, 34.2, 32.1, 34.8, 36.5, 33.9, 40.1],
        pago: [31.5, 29.8, 34.8, 33.9, 31.2, 34.2, 32.8, 30.9, 33.2, 35.1, 32.5, 38.5]
    },
    licitacoes: [
        { numero: "PE 001/2026", objeto: "Aquisição de medicamentos", valor: 2500000, modalidade: "Pregão Eletrônico", status: "Em andamento", data: "2026-01-18" },
        { numero: "PE 002/2026", objeto: "Serviços de limpeza hospitalar", valor: 1800000, modalidade: "Pregão Eletrônico", status: "Homologada", data: "2026-01-15" },
        { numero: "CC 001/2026", objeto: "Reforma de escola municipal", valor: 3200000, modalidade: "Concorrência", status: "Em andamento", data: "2026-01-12" },
        { numero: "PE 003/2026", objeto: "Material de escritório", valor: 150000, modalidade: "Pregão Eletrônico", status: "Homologada", data: "2026-01-10" },
        { numero: "DL 001/2026", objeto: "Manutenção emergencial", valor: 45000, modalidade: "Dispensa", status: "Contratada", data: "2026-01-08" }
    ],
    fornecedores: [
        { nome: "DISTRIBUIDORA FARMA LTDA", cnpj: "12.345.678/0001-90", valor: 8500000, contratos: 5 },
        { nome: "CONSTRUTORA ABC S/A", cnpj: "98.765.432/0001-10", valor: 6200000, contratos: 3 },
        { nome: "SERVIÇOS GERAIS ME", cnpj: "11.222.333/0001-44", valor: 4800000, contratos: 8 },
        { nome: "TECNOLOGIA INFO LTDA", cnpj: "55.666.777/0001-88", valor: 3200000, contratos: 4 },
        { nome: "ALIMENTOS E CIA EIRELI", cnpj: "22.333.444/0001-55", valor: 2900000, contratos: 6 }
    ]
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
        }
    } catch (e) {
        console.log('Usando dados de exemplo');
    }
    window.DASHBOARD_DATA = DASHBOARD_DATA;
})();

// Disponibilizar globalmente
window.DASHBOARD_DATA = DASHBOARD_DATA;
