/**
 * MonitoraMarília - Dados do Dashboard
 * Dados de exemplo para demonstração
 * Em produção, estes dados são gerados pelo sistema Python
 */

const DASHBOARD_DATA = {
    // Última atualização
    lastUpdate: new Date().toISOString(),

    // KPIs principais
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

    // Checklist LAI (Lei 12.527/2011, Art. 8º, §1º)
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

    // Alertas ativos
    alertas: [
        {
            id: 1,
            tipo: "critico",
            titulo: "Contrato sem licitação - valor elevado",
            descricao: "Contrato nº 2024/089 no valor de R$ 890.000,00 firmado por dispensa de licitação. Verificar enquadramento legal.",
            data: "2024-01-15",
            categoria: "contratos"
        },
        {
            id: 2,
            tipo: "critico",
            titulo: "Possível fracionamento de despesas",
            descricao: "Detectadas 5 compras de material de escritório no mesmo mês, totalizando R$ 78.000,00, com mesmo fornecedor.",
            data: "2024-01-12",
            categoria: "despesas"
        },
        {
            id: 3,
            tipo: "alerta",
            titulo: "Atraso na atualização de despesas",
            descricao: "Dados de despesas não atualizados há 3 dias. LAI exige atualização em tempo real.",
            data: "2024-01-18",
            categoria: "lai"
        },
        {
            id: 4,
            tipo: "alerta",
            titulo: "Fornecedor com alta concentração",
            descricao: "Empresa XYZ LTDA recebeu 15% do total de pagamentos do mês de dezembro/2023.",
            data: "2024-01-10",
            categoria: "fornecedores"
        },
        {
            id: 5,
            tipo: "info",
            titulo: "Aditivo contratual acima de 25%",
            descricao: "Contrato nº 2023/045 teve aditivo de 32%, superando o limite legal de 25%.",
            data: "2024-01-08",
            categoria: "contratos"
        },
        {
            id: 6,
            tipo: "info",
            titulo: "Licitação deserta",
            descricao: "Pregão Eletrônico nº 012/2024 declarado deserto. Nova licitação necessária.",
            data: "2024-01-05",
            categoria: "licitacoes"
        },
        {
            id: 7,
            tipo: "info",
            titulo: "Dados de folha de pagamento",
            descricao: "Folha de dezembro/2023 publicada com 15 dias de atraso.",
            data: "2024-01-03",
            categoria: "pessoal"
        }
    ],

    // Despesas por categoria (para gráfico de pizza)
    despesasPorCategoria: {
        labels: ["Pessoal", "Custeio", "Investimentos", "Saúde", "Educação", "Outros"],
        data: [45, 20, 10, 12, 8, 5],
        valores: ["R$ 180M", "R$ 80M", "R$ 40M", "R$ 48M", "R$ 32M", "R$ 20M"]
    },

    // Evolução mensal de despesas (para gráfico de barras)
    despesasMensais: {
        labels: ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"],
        empenhado: [35.2, 32.1, 38.5, 36.8, 34.2, 37.9, 35.6, 33.8, 36.2, 38.1, 35.4, 42.3],
        liquidado: [33.1, 30.5, 36.2, 35.1, 32.8, 35.6, 34.2, 32.1, 34.8, 36.5, 33.9, 40.1],
        pago: [31.5, 29.8, 34.8, 33.9, 31.2, 34.2, 32.8, 30.9, 33.2, 35.1, 32.5, 38.5]
    },

    // Últimas licitações
    licitacoes: [
        { numero: "PE 001/2024", objeto: "Aquisição de medicamentos", valor: 2500000, modalidade: "Pregão Eletrônico", status: "Em andamento", data: "2024-01-18" },
        { numero: "PE 002/2024", objeto: "Serviços de limpeza hospitalar", valor: 1800000, modalidade: "Pregão Eletrônico", status: "Homologada", data: "2024-01-15" },
        { numero: "CC 001/2024", objeto: "Reforma de escola municipal", valor: 3200000, modalidade: "Concorrência", status: "Em andamento", data: "2024-01-12" },
        { numero: "PE 003/2024", objeto: "Material de escritório", valor: 150000, modalidade: "Pregão Eletrônico", status: "Homologada", data: "2024-01-10" },
        { numero: "DL 001/2024", objeto: "Manutenção emergencial", valor: 45000, modalidade: "Dispensa", status: "Contratada", data: "2024-01-08" }
    ],

    // Maiores fornecedores
    fornecedores: [
        { nome: "DISTRIBUIDORA FARMA LTDA", cnpj: "12.345.678/0001-90", valor: 8500000, contratos: 5 },
        { nome: "CONSTRUTORA ABC S/A", cnpj: "98.765.432/0001-10", valor: 6200000, contratos: 3 },
        { nome: "SERVIÇOS GERAIS ME", cnpj: "11.222.333/0001-44", valor: 4800000, contratos: 8 },
        { nome: "TECNOLOGIA INFO LTDA", cnpj: "55.666.777/0001-88", valor: 3200000, contratos: 4 },
        { nome: "ALIMENTOS E CIA EIRELI", cnpj: "22.333.444/0001-55", valor: 2900000, contratos: 6 }
    ]
};

// Exportar para uso global
if (typeof window !== 'undefined') {
    window.DASHBOARD_DATA = DASHBOARD_DATA;
}
