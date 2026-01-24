/**
 * MonitoraMarília - Configuração de Gráficos
 * Utiliza Chart.js para visualização de dados integrados
 *
 * Fontes: SICONFI, TCE-SP, Portal Federal
 */

// Cores do tema
const CHART_COLORS = {
    primary: '#1e3a5f',
    secondary: '#2d5a87',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    info: '#3b82f6',
    purple: '#8b5cf6',
    pink: '#ec4899',
    gray: '#6b7280'
};

// Paleta para gráficos
const COLOR_PALETTE = [
    '#1e3a5f', '#2d5a87', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'
];

/**
 * Inicializa o gráfico de despesas por órgão/categoria (Pizza/Doughnut)
 */
function initDespesasChart() {
    const ctx = document.getElementById('despesasChart');
    if (!ctx) return;

    const data = DASHBOARD_DATA.graficos?.despesasPorOrgao || {
        labels: ["Saúde", "Educação", "Administração", "Obras", "Assistência Social", "Outros"],
        valores: [35, 28, 15, 10, 7, 5]
    };

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.valores,
                backgroundColor: COLOR_PALETTE,
                borderColor: '#ffffff',
                borderWidth: 2,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 1.5,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 15,
                        usePointStyle: true,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            return `${label}: ${value}%`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Inicializa o gráfico de evolução mensal de despesas (Barras)
 * Dados do TCE-SP
 */
function initEvolucaoChart() {
    const ctx = document.getElementById('evolucaoChart');
    if (!ctx) return;

    const data = DASHBOARD_DATA.graficos?.evolucaoMensal || {
        labels: ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"],
        empenhado: [35.2, 32.1, 38.5, 36.8, 34.2, 37.9, 35.6, 33.8, 36.2, 38.1, 35.4, 42.3],
        liquidado: [33.1, 30.5, 36.2, 35.1, 32.8, 35.6, 34.2, 32.1, 34.8, 36.5, 33.9, 40.1],
        pago: [31.5, 29.8, 34.8, 33.9, 31.2, 34.2, 32.8, 30.9, 33.2, 35.1, 32.5, 38.5]
    };

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Empenhado',
                    data: data.empenhado,
                    backgroundColor: CHART_COLORS.info,
                    borderRadius: 4
                },
                {
                    label: 'Liquidado',
                    data: data.liquidado,
                    backgroundColor: CHART_COLORS.warning,
                    borderRadius: 4
                },
                {
                    label: 'Pago',
                    data: data.pago,
                    backgroundColor: CHART_COLORS.success,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            aspectRatio: 2,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        padding: 10,
                        usePointStyle: true,
                        font: {
                            size: 11
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.dataset.label}: R$ ${context.parsed.y.toFixed(1)}M`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        font: {
                            size: 10
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: '#f3f4f6'
                    },
                    ticks: {
                        callback: function(value) {
                            return 'R$ ' + value + 'M';
                        },
                        font: {
                            size: 10
                        }
                    }
                }
            }
        }
    });
}

/**
 * Inicializa todos os gráficos
 */
function initAllCharts() {
    initDespesasChart();
    initEvolucaoChart();
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', function() {
    // Aguarda os dados carregarem
    setTimeout(function() {
        if (typeof DASHBOARD_DATA !== 'undefined') {
            initAllCharts();
        }
    }, 150);
});
