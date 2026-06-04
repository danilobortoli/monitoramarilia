/**
 * MonitoraMarília - Lógica Principal do Dashboard
 *
 * Renderiza dados integrados de múltiplas fontes:
 * - SICONFI: Indicadores fiscais (RCL, LRF)
 * - TCE-SP: Execução orçamentária, fornecedores
 * - Portal Federal: Transferências, convênios, sanções
 */

const PLACEHOLDER = '—';

document.addEventListener('DOMContentLoaded', function() {
    // Aguardar carregamento dos dados
    setTimeout(initDashboard, 100);
});

/**
 * Inicializa o dashboard
 */
function initDashboard() {
    updateLastUpdate();
    renderFiscalKPIs();
    renderTransferencias();
    renderExecucaoTCE();
    renderFornecedores();
    renderSancoes();
    renderAlerts();
    showDataWarningIfNeeded();
}

// Expor globalmente para recarregamento
window.initDashboard = initDashboard;

/**
 * Mostra aviso se os dados não foram carregados
 */
function showDataWarningIfNeeded() {
    if (!DASHBOARD_DATA.dadosCarregados) {
        const alertContainer = document.getElementById('alerts-list');
        if (alertContainer) {
            alertContainer.innerHTML = `
                <div class="note" data-tipo="alerta">
                    <p class="note__title">Dados ainda não coletados</p>
                    <p class="note__desc">Os indicadores são obtidos das APIs oficiais. Rode
                        <code>python -m src.main update-dashboard</code> para carregar SICONFI, TCE&#8209;SP e Portal Federal.</p>
                </div>
            `;
        }
    }
}

/**
 * Atualiza a data da última atualização
 */
function updateLastUpdate() {
    const element = document.getElementById('last-update');
    if (element) {
        if (DASHBOARD_DATA.lastUpdate) {
            const date = new Date(DASHBOARD_DATA.lastUpdate);
            element.textContent = date.toLocaleString('pt-BR', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } else {
            element.textContent = 'ainda não coletada';
        }
    }
}

/**
 * Renderiza os KPIs fiscais (SICONFI)
 */
function renderFiscalKPIs() {
    const fiscal = DASHBOARD_DATA.fiscal;
    if (!fiscal) return;

    // RCL
    setElementText('rcl-valor', fiscal.rclFormatado || formatCurrency(fiscal.rcl) || PLACEHOLDER);

    // Despesa com Pessoal
    const pessoal = fiscal.despesaPessoal;
    if (pessoal) {
        if (pessoal.percentual !== null && pessoal.percentual !== undefined) {
            setElementText('pessoal-percentual', `${pessoal.percentual.toFixed(1)}%`);
            updateLimitCard('pessoal', pessoal.percentual, pessoal.limite, pessoal.status);
        } else {
            setElementText('pessoal-percentual', PLACEHOLDER);
        }
    }

    // Dívida Consolidada
    const divida = fiscal.divida;
    if (divida) {
        if (divida.percentual !== null && divida.percentual !== undefined) {
            setElementText('divida-percentual', `${divida.percentual.toFixed(1)}%`);
            updateLimitCard('divida', divida.percentual, divida.limite, divida.status);
        } else {
            setElementText('divida-percentual', PLACEHOLDER);
        }
    }

    // Alertas LRF
    const alertasLRF = fiscal.alertasLRF || [];
    const alertasCriticos = alertasLRF.filter(a => a.tipo === 'critico').length;
    setElementText('alertas-lrf-count', alertasLRF.length);
    setElementText('alertas-criticos', alertasCriticos);
}

/**
 * Atualiza um indicador de limite (pessoal/dívida) com a régua de status
 */
function updateLimitCard(tipo, percentual, limite, status) {
    const bar = document.getElementById(`${tipo}-bar`);
    const statusEl = document.getElementById(`${tipo}-status`);

    // Régua (bullet): preenchimento relativo ao teto
    if (bar && percentual !== null && percentual !== undefined) {
        bar.style.width = `${Math.min(percentual / limite * 100, 100)}%`;
        if (status) bar.setAttribute('data-status', status);
    }

    // Texto de status
    if (statusEl) {
        const rotulo = {
            ok: 'dentro do limite',
            alerta: 'limite de alerta',
            prudencial: 'limite prudencial',
            critico: 'acima do limite'
        }[status] || '';
        statusEl.textContent = rotulo ? `${rotulo} · teto ${limite}% da RCL` : `teto ${limite}% da RCL`;
        if (status) statusEl.setAttribute('data-status', status);
    }
}

/**
 * Renderiza transferências federais
 */
function renderTransferencias() {
    const transf = DASHBOARD_DATA.transferencias;
    const conv = DASHBOARD_DATA.convenios;
    const emendas = DASHBOARD_DATA.emendas;

    if (transf) {
        const valor = transf.totalFmt || formatCurrency(transf.total);
        setElementText('transf-total', valor || PLACEHOLDER);
    }

    if (conv) {
        setElementText('convenios-count', conv.quantidade !== null ? conv.quantidade : '--');
        const valorConv = conv.valorFmt || formatCurrency(conv.valorTotal);
        setElementText('convenios-valor', valorConv || PLACEHOLDER);
    }

    if (emendas) {
        const valorEmendas = emendas.valorFmt || formatCurrency(emendas.valorTotal);
        setElementText('emendas-valor', valorEmendas || PLACEHOLDER);
        setElementText('emendas-count', emendas.quantidade !== null ? `${emendas.quantidade} emendas` : '--');
    }
}

/**
 * Renderiza dados de execução do TCE-SP
 */
function renderExecucaoTCE() {
    const exec = DASHBOARD_DATA.execucao;
    if (!exec) return;

    const empenhado = exec.empenhadoFmt || formatCurrency(exec.empenhado);
    const liquidado = exec.liquidadoFmt || formatCurrency(exec.liquidado);
    const pago = exec.pagoFmt || formatCurrency(exec.pago);

    setElementText('tce-empenhado', empenhado || PLACEHOLDER);
    setElementText('tce-liquidado', liquidado || PLACEHOLDER);
    setElementText('tce-pago', pago || PLACEHOLDER);
}

/**
 * Renderiza os maiores fornecedores
 */
function renderFornecedores() {
    const container = document.getElementById('fornecedores-list');
    if (!container) return;

    const fornecedores = DASHBOARD_DATA.fornecedores?.top10 || [];

    if (fornecedores.length === 0) {
        container.innerHTML = `<p class="empty">Dados de fornecedores ainda não coletados.
            Rode <code>python -m src.main update-dashboard</code>.</p>`;
        return;
    }

    const maxValor = Math.max(...fornecedores.map(f => f.valor));

    container.className = 'rows';
    container.innerHTML = fornecedores.slice(0, 8).map((forn, index) => {
        const percentage = (forn.valor / maxValor) * 100;
        const irregular = forn.situacaoSancoes && forn.situacaoSancoes !== 'REGULAR';
        const marca = irregular ? ' ⚠' : '';
        return `
            <div class="row">
                <span class="row__rank">${index + 1}</span>
                <span class="row__name">${forn.nome}${marca}
                    <span class="meta">· ${forn.qtdPagamentos} pgtos</span></span>
                <span class="row__val">${forn.valorFmt || formatCurrency(forn.valor)}</span>
                <span class="micro"><i style="width:${percentage}%"></i></span>
            </div>
        `;
    }).join('');
}

/**
 * Renderiza informações de sanções
 */
function renderSancoes() {
    const sancoes = DASHBOARD_DATA.fornecedores?.sancoesVerificadas;

    setElementText('sancoes-verificados', sancoes?.total ?? '--');
    setElementText('sancoes-irregulares', sancoes?.irregulares ?? '--');

    const container = document.getElementById('sancoes-list');
    const emptyMsg = document.getElementById('sancoes-empty');

    if (!container) return;

    if (sancoes?.alertas && sancoes.alertas.length > 0) {
        if (emptyMsg) emptyMsg.style.display = 'none';

        container.innerHTML = sancoes.alertas.map(alerta => `
            <div class="note" data-tipo="critico">
                <p class="note__title">${alerta.titulo}</p>
                <p class="note__desc">${alerta.descricao}</p>
                <p class="note__tag">${alerta.cnpj || ''}</p>
            </div>
        `).join('');
    } else {
        if (emptyMsg) emptyMsg.style.display = 'block';
    }
}

/**
 * Renderiza os alertas
 */
function renderAlerts() {
    const container = document.getElementById('alerts-list');
    if (!container) return;

    // Se dados não carregados, showDataWarningIfNeeded() cuida disso
    if (!DASHBOARD_DATA.dadosCarregados) {
        return;
    }

    // Consolidar todos os alertas
    const alertas = [
        ...(DASHBOARD_DATA.fiscal?.alertasLRF || []),
        ...(DASHBOARD_DATA.alertas?.lrf || []),
        ...(DASHBOARD_DATA.alertas?.fornecedores || []),
        ...(DASHBOARD_DATA.alertas?.outros || [])
    ].slice(0, 5);

    if (alertas.length === 0) {
        container.innerHTML = `<p class="empty">Nenhum alerta ativo no momento.</p>`;
        return;
    }

    const tipoNorm = t => (t === 'critico' || t === 'alerta') ? t : 'info';

    container.innerHTML = alertas.map(alerta => `
        <div class="note" data-tipo="${tipoNorm(alerta.tipo)}">
            <p class="note__title">${alerta.titulo}<span class="when">${formatDate(alerta.data)}</span></p>
            <p class="note__desc">${alerta.descricao}</p>
            <p class="note__tag">${alerta.categoria || ''}</p>
        </div>
    `).join('');
}

// ============ FUNÇÕES AUXILIARES ============

function setElementText(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value !== undefined && value !== null ? value : PLACEHOLDER;
    }
}

function formatCurrency(value) {
    if (value === null || value === undefined) {
        return null;
    }
    if (value >= 1000000) {
        return 'R$ ' + (value / 1000000).toLocaleString('pt-BR', {
            minimumFractionDigits: 1,
            maximumFractionDigits: 1
        }) + 'M';
    }
    return 'R$ ' + value.toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatDate(dateStr) {
    if (!dateStr) return '--';
    const date = new Date(dateStr);
    return date.toLocaleDateString('pt-BR');
}
