/**
 * MonitoraMarília — Gráficos (estilo Tufte · Bortoli)
 *
 * Princípios: pouca tinta, sem grades pesadas, sem dados inventados.
 * Quando não há dado real coletado, mostramos um estado vazio honesto
 * em vez de números fabricados.
 *
 * Fontes: TCE-SP (execução e despesa por função).
 */

const INK   = '#141414';
const MUTED  = '#767066';
const RULE  = '#ece7da';
const SERIES = { empenhado: '#2c3e50', liquidado: '#8a6d00', pago: '#2f6b3f' };
const BAR    = '#3a4a59';

// Defaults sóbrios para todos os gráficos
if (window.Chart) {
    Chart.defaults.font.family = "'et-book','Iowan Old Style',Palatino,Georgia,serif";
    Chart.defaults.font.size = 12;
    Chart.defaults.color = MUTED;
    Chart.defaults.plugins.legend.display = false; // legenda é feita em HTML
    Chart.defaults.plugins.tooltip.backgroundColor = INK;
    Chart.defaults.plugins.tooltip.cornerRadius = 0;
    Chart.defaults.plugins.tooltip.displayColors = false;
}

/** Substitui o gráfico por uma nota honesta de "sem dados". */
function renderEmpty(canvasId, mensagem) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const box = canvas.closest('.chart-box') || canvas.parentElement;
    box.innerHTML = `<p class="chart-empty">${mensagem}</p>`;
}

function temDados(arr) { return Array.isArray(arr) && arr.length > 0; }

/** Despesa por função — barras horizontais (Tufte prefere barra a pizza). */
function initDespesasChart() {
    const ctx = document.getElementById('despesasChart');
    if (!ctx) return;

    const data = DASHBOARD_DATA.graficos?.despesasPorOrgao;
    if (!data || !temDados(data.labels) || !temDados(data.valores)) {
        renderEmpty('despesasChart', 'Sem dados de despesa por função coletados ainda.');
        return;
    }

    const emMilhoes = data.valores.map(v => v > 100000 ? v / 1e6 : v);

    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{ data: emMilhoes, backgroundColor: BAR, borderWidth: 0, barPercentage: 0.7 }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                tooltip: { callbacks: { label: c => ` R$ ${c.parsed.x.toFixed(1)} mi` } }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    border: { display: false },
                    grid: { color: RULE, drawTicks: false },
                    ticks: { callback: v => `${v}` }
                },
                y: { border: { display: false }, grid: { display: false } }
            }
        }
    });
}

/** Execução mensal — linhas finas (empenhado / liquidado / pago). */
function initEvolucaoChart() {
    const ctx = document.getElementById('evolucaoChart');
    if (!ctx) return;

    const data = DASHBOARD_DATA.graficos?.evolucaoMensal;
    if (!data || !temDados(data.labels)) {
        renderEmpty('evolucaoChart', 'Sem série mensal de execução coletada ainda.');
        return;
    }

    const linha = (chave, cor) => ({
        label: chave,
        data: data[chave] || [],
        borderColor: cor,
        backgroundColor: cor,
        borderWidth: 1.5,
        pointRadius: 0,
        pointHoverRadius: 3,
        tension: 0.15,
        spanGaps: true
    });

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [
                linha('empenhado', SERIES.empenhado),
                linha('liquidado', SERIES.liquidado),
                linha('pago', SERIES.pago)
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                tooltip: { callbacks: { label: c => ` ${c.dataset.label}: R$ ${Number(c.parsed.y).toFixed(1)} mi` } }
            },
            scales: {
                x: { border: { display: false }, grid: { display: false } },
                y: {
                    beginAtZero: true,
                    border: { display: false },
                    grid: { color: RULE, drawTicks: false },
                    ticks: { callback: v => `${v}` }
                }
            }
        }
    });
}

function initAllCharts() {
    initDespesasChart();
    initEvolucaoChart();
}

document.addEventListener('DOMContentLoaded', function () {
    setTimeout(function () {
        if (typeof DASHBOARD_DATA !== 'undefined') initAllCharts();
    }, 150);
});
