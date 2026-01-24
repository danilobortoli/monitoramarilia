/**
 * MonitoraMarília - Configuração de Gráficos
 * Utiliza Chart.js para visualização de dados
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
 * Inicializa o gráfico de despesas por categoria (Pizza/Doughnut)
 */
function initDespesasChart() {
    const ctx = document.getElementById('despesasChart');
    if (!ctx) return;

    const data = DASHBOARD_DATA.despesasPorCategoria;

    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.data,
                backgroundColor: COLOR_PALETTE,
                borderColor: '#ffffff',
                borderWidth: 2,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        padding: 15,
                        usePointStyle: true,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const valorReal = data.valores[context.dataIndex];
                            return `${label}: ${value}% (${valorReal})`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * Inicializa o gráfico de evolução mensal de despesas (Barras)
 */
function initEvolucaoChart() {
    const ctx = document.getElementById('evolucaoChart');
    if (!ctx) return;

    const data = DASHBOARD_DATA.despesasMensais;

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Empenhado',
                    data: data.empenhado,
                    backgroundColor: CHART_COLORS.primary,
                    borderRadius: 4
                },
                {
                    label: 'Liquidado',
                    data: data.liquidado,
                    backgroundColor: CHART_COLORS.secondary,
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
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        padding: 15,
                        usePointStyle: true
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
    if (typeof DASHBOARD_DATA !== 'undefined') {
        initAllCharts();
    }
});
