/**
 * MonitoraMarília - Lógica Principal do Dashboard
 *
 * Renderiza dados integrados de múltiplas fontes:
 * - SICONFI: Indicadores fiscais (RCL, LRF)
 * - TCE-SP: Execução orçamentária, fornecedores
 * - Portal Federal: Transferências, convênios, sanções
 */

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
}

// Expor globalmente para recarregamento
window.initDashboard = initDashboard;

/**
 * Atualiza a data da última atualização
 */
function updateLastUpdate() {
    const element = document.getElementById('last-update');
    if (element && DASHBOARD_DATA.lastUpdate) {
        const date = new Date(DASHBOARD_DATA.lastUpdate);
        element.textContent = date.toLocaleString('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
}

/**
 * Renderiza os KPIs fiscais (SICONFI)
 */
function renderFiscalKPIs() {
    const fiscal = DASHBOARD_DATA.fiscal;
    if (!fiscal) return;

    // RCL
    setElementText('rcl-valor', fiscal.rclFormatado || formatCurrency(fiscal.rcl));

    // Despesa com Pessoal
    const pessoal = fiscal.despesaPessoal;
    if (pessoal) {
        setElementText('pessoal-percentual', `${pessoal.percentual.toFixed(1)}%`);
        updateLimitCard('pessoal', pessoal.percentual, pessoal.limite, pessoal.status);
    }

    // Dívida Consolidada
    const divida = fiscal.divida;
    if (divida) {
        setElementText('divida-percentual', `${divida.percentual.toFixed(1)}%`);
        updateLimitCard('divida', divida.percentual, divida.limite, divida.status);
    }

    // Alertas LRF
    const alertasLRF = fiscal.alertasLRF || [];
    const alertasCriticos = alertasLRF.filter(a => a.tipo === 'critico').length;
    setElementText('alertas-lrf-count', alertasLRF.length);
    setElementText('alertas-criticos', alertasCriticos);
}

/**
 * Atualiza um card de limite (pessoal/dívida)
 */
function updateLimitCard(tipo, percentual, limite, status) {
    const card = document.getElementById(`${tipo}-card`);
    const bar = document.getElementById(`${tipo}-bar`);
    const statusEl = document.getElementById(`${tipo}-status`);
    const icon = document.getElementById(`${tipo}-icon`);

    if (!card) return;

    // Calcular cor baseado no status
    let borderColor, barColor, iconColor, textColor;

    switch (status) {
        case 'ok':
            borderColor = 'border-green-500';
            barColor = 'bg-green-500';
            iconColor = 'bg-green-100';
            textColor = 'text-green-600';
            break;
        case 'alerta':
            borderColor = 'border-yellow-500';
            barColor = 'bg-yellow-500';
            iconColor = 'bg-yellow-100';
            textColor = 'text-yellow-600';
            break;
        case 'prudencial':
            borderColor = 'border-orange-500';
            barColor = 'bg-orange-500';
            iconColor = 'bg-orange-100';
            textColor = 'text-orange-600';
            break;
        case 'critico':
            borderColor = 'border-red-500';
            barColor = 'bg-red-500';
            iconColor = 'bg-red-100';
            textColor = 'text-red-600';
            break;
        default:
            borderColor = 'border-gray-500';
            barColor = 'bg-gray-500';
            iconColor = 'bg-gray-100';
            textColor = 'text-gray-600';
    }

    // Atualizar card
    card.className = card.className.replace(/border-l-4 border-\w+-500/g, '');
    card.classList.add('border-l-4', borderColor);

    // Atualizar barra de progresso
    if (bar) {
        bar.className = `h-2 rounded-full transition-all ${barColor}`;
        bar.style.width = `${Math.min(percentual / limite * 100, 100)}%`;
    }

    // Atualizar texto de status
    if (statusEl) {
        statusEl.className = `text-sm mt-1 ${textColor}`;
        const statusIcon = status === 'ok' ? 'fa-check-circle' :
                          status === 'critico' ? 'fa-times-circle' : 'fa-exclamation-circle';
        statusEl.innerHTML = `<i class="fas ${statusIcon} mr-1"></i>Limite: ${limite}% da RCL`;
    }

    // Atualizar ícone
    if (icon) {
        icon.className = `p-4 rounded-full ${iconColor}`;
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
        setElementText('transf-total', transf.totalFmt || formatCurrency(transf.total));
    }

    if (conv) {
        setElementText('convenios-count', conv.quantidade);
        setElementText('convenios-valor', conv.valorFmt || formatCurrency(conv.valorTotal));
    }

    if (emendas) {
        setElementText('emendas-valor', emendas.valorFmt || formatCurrency(emendas.valorTotal));
        setElementText('emendas-count', `${emendas.quantidade} emendas`);
    }
}

/**
 * Renderiza dados de execução do TCE-SP
 */
function renderExecucaoTCE() {
    const exec = DASHBOARD_DATA.execucao;
    if (!exec) return;

    setElementText('tce-empenhado', exec.empenhadoFmt || formatCurrency(exec.empenhado));
    setElementText('tce-liquidado', exec.liquidadoFmt || formatCurrency(exec.liquidado));
    setElementText('tce-pago', exec.pagoFmt || formatCurrency(exec.pago));
}

/**
 * Renderiza os maiores fornecedores
 */
function renderFornecedores() {
    const container = document.getElementById('fornecedores-list');
    if (!container) return;

    const fornecedores = DASHBOARD_DATA.fornecedores?.top10 || [];

    if (fornecedores.length === 0) {
        container.innerHTML = '<p class="text-gray-500 text-center py-4">Nenhum dado disponível</p>';
        return;
    }

    const maxValor = Math.max(...fornecedores.map(f => f.valor));

    container.innerHTML = fornecedores.slice(0, 5).map((forn, index) => {
        const percentage = (forn.valor / maxValor) * 100;
        const statusColor = forn.situacaoSancoes === 'REGULAR' ? 'text-green-600' : 'text-red-600';
        const statusIcon = forn.situacaoSancoes === 'REGULAR' ? 'fa-check-circle' : 'fa-exclamation-circle';

        return `
            <div class="p-3 hover:bg-gray-50 transition rounded-lg">
                <div class="flex items-center justify-between mb-1">
                    <div class="flex items-center space-x-2">
                        <span class="w-6 h-6 flex items-center justify-center bg-blue-100 text-blue-600 rounded-full text-xs font-bold">${index + 1}</span>
                        <span class="text-sm font-medium text-gray-800 truncate max-w-[180px]">${forn.nome}</span>
                        <i class="fas ${statusIcon} ${statusColor} text-xs" title="${forn.situacaoSancoes}"></i>
                    </div>
                    <span class="text-sm font-semibold text-gray-800">${forn.valorFmt || formatCurrency(forn.valor)}</span>
                </div>
                <div class="flex items-center space-x-2 ml-8">
                    <div class="flex-1 bg-gray-200 rounded-full h-2">
                        <div class="bg-blue-600 h-2 rounded-full" style="width: ${percentage}%"></div>
                    </div>
                    <span class="text-xs text-gray-500">${forn.qtdPagamentos} pgtos</span>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Renderiza informações de sanções
 */
function renderSancoes() {
    const sancoes = DASHBOARD_DATA.fornecedores?.sancoesVerificadas;
    if (!sancoes) return;

    setElementText('sancoes-verificados', sancoes.total);
    setElementText('sancoes-irregulares', sancoes.irregulares);

    const container = document.getElementById('sancoes-list');
    const emptyMsg = document.getElementById('sancoes-empty');

    if (!container) return;

    if (sancoes.alertas && sancoes.alertas.length > 0) {
        if (emptyMsg) emptyMsg.style.display = 'none';

        container.innerHTML = sancoes.alertas.map(alerta => `
            <div class="flex items-start space-x-3 p-3 bg-red-50 rounded-lg border border-red-200">
                <i class="fas fa-exclamation-triangle text-red-500 mt-1"></i>
                <div class="flex-1">
                    <p class="text-sm font-medium text-red-800">${alerta.titulo}</p>
                    <p class="text-xs text-red-600">${alerta.descricao}</p>
                    <span class="text-xs text-gray-500">${alerta.cnpj}</span>
                </div>
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

    // Consolidar todos os alertas
    const alertas = [
        ...(DASHBOARD_DATA.fiscal?.alertasLRF || []),
        ...(DASHBOARD_DATA.alertas?.lrf || []),
        ...(DASHBOARD_DATA.alertas?.fornecedores || []),
        ...(DASHBOARD_DATA.alertas?.outros || [])
    ].slice(0, 5);

    if (alertas.length === 0) {
        container.innerHTML = `
            <div class="text-center py-8 text-gray-500">
                <i class="fas fa-check-circle text-4xl text-green-500 mb-2"></i>
                <p>Nenhum alerta ativo no momento.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = alertas.map(alerta => {
        const tipoConfig = getAlertConfig(alerta.tipo);

        return `
            <div class="flex items-start space-x-4 p-4 border-l-4 ${tipoConfig.borderClass} bg-gray-50 rounded-r-lg hover:bg-gray-100 transition">
                <div class="flex-shrink-0">
                    <span class="w-10 h-10 flex items-center justify-center rounded-full ${tipoConfig.bgClass}">
                        <i class="${tipoConfig.icon} ${tipoConfig.textClass}"></i>
                    </span>
                </div>
                <div class="flex-1">
                    <div class="flex items-center justify-between">
                        <h4 class="text-sm font-semibold text-gray-800">${alerta.titulo}</h4>
                        <span class="text-xs text-gray-500">${formatDate(alerta.data)}</span>
                    </div>
                    <p class="text-sm text-gray-600 mt-1">${alerta.descricao}</p>
                    <span class="inline-block mt-2 text-xs px-2 py-1 rounded-full bg-gray-200 text-gray-600">${alerta.categoria}</span>
                </div>
            </div>
        `;
    }).join('');
}

// ============ FUNÇÕES AUXILIARES ============

function setElementText(id, value) {
    const element = document.getElementById(id);
    if (element && value !== undefined) {
        element.textContent = value;
    }
}

function getStatusClass(status) {
    switch (status) {
        case 'ok': return 'bg-green-500';
        case 'warning': return 'bg-yellow-500';
        case 'error': return 'bg-red-500';
        default: return 'bg-gray-500';
    }
}

function getStatusIcon(status) {
    switch (status) {
        case 'ok': return 'fas fa-check';
        case 'warning': return 'fas fa-exclamation';
        case 'error': return 'fas fa-times';
        default: return 'fas fa-question';
    }
}

function getStatusText(status) {
    switch (status) {
        case 'ok': return 'Conforme';
        case 'warning': return 'Atenção';
        case 'error': return 'Irregular';
        default: return 'Pendente';
    }
}

function getAlertConfig(tipo) {
    switch (tipo) {
        case 'critico':
            return {
                borderClass: 'border-red-500',
                bgClass: 'bg-red-100',
                textClass: 'text-red-600',
                icon: 'fas fa-exclamation-circle'
            };
        case 'alerta':
            return {
                borderClass: 'border-yellow-500',
                bgClass: 'bg-yellow-100',
                textClass: 'text-yellow-600',
                icon: 'fas fa-exclamation-triangle'
            };
        default:
            return {
                borderClass: 'border-blue-500',
                bgClass: 'bg-blue-100',
                textClass: 'text-blue-600',
                icon: 'fas fa-info-circle'
            };
    }
}

function formatCurrency(value) {
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
