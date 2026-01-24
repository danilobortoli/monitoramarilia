/**
 * MonitoraMarília - Lógica Principal do Dashboard
 */

document.addEventListener('DOMContentLoaded', function() {
    initDashboard();
});

/**
 * Inicializa o dashboard
 */
function initDashboard() {
    updateLastUpdate();
    updateKPIs();
    renderLAIChecklist();
    renderAlerts();
    renderLicitacoes();
    renderFornecedores();
}

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

    const laiCheckDate = document.getElementById('lai-check-date');
    if (laiCheckDate) {
        laiCheckDate.textContent = new Date().toLocaleDateString('pt-BR');
    }
}

/**
 * Atualiza os KPIs do dashboard
 */
function updateKPIs() {
    const kpis = DASHBOARD_DATA.kpis;

    setElementText('lai-score', kpis.laiScore);
    setElementText('lai-items', kpis.laiItems);
    setElementText('licitacoes-count', kpis.licitacoesCount);
    setElementText('licitacoes-valor', kpis.licitacoesValor);
    setElementText('contratos-count', kpis.contratosCount);
    setElementText('contratos-aditivos', kpis.contratosAditivos);
    setElementText('alertas-count', kpis.alertasCount);
    setElementText('alertas-criticos', kpis.alertasCriticos);
}

/**
 * Renderiza o checklist de conformidade LAI
 */
function renderLAIChecklist() {
    const container = document.getElementById('lai-checklist');
    if (!container) return;

    const items = DASHBOARD_DATA.laiChecklist;
    container.innerHTML = items.map(item => {
        const statusClass = getStatusClass(item.status);
        const statusIcon = getStatusIcon(item.status);
        const statusText = getStatusText(item.status);

        return `
            <div class="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition">
                <div class="flex items-center space-x-3">
                    <span class="w-8 h-8 flex items-center justify-center rounded-full ${statusClass}">
                        <i class="${statusIcon} text-white text-sm"></i>
                    </span>
                    <div>
                        <p class="text-sm font-medium text-gray-800">${item.item}</p>
                        ${item.note ? `<p class="text-xs text-gray-500">${item.note}</p>` : ''}
                    </div>
                </div>
                <span class="text-xs font-medium ${statusClass.replace('bg-', 'text-').replace('-500', '-600')}">${statusText}</span>
            </div>
        `;
    }).join('');
}

/**
 * Renderiza os alertas
 */
function renderAlerts() {
    const container = document.getElementById('alerts-list');
    if (!container) return;

    const alertas = DASHBOARD_DATA.alertas.slice(0, 5); // Mostrar apenas os 5 primeiros

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

/**
 * Renderiza as últimas licitações
 */
function renderLicitacoes() {
    const container = document.getElementById('licitacoes-list');
    if (!container) return;

    const licitacoes = DASHBOARD_DATA.licitacoes;

    container.innerHTML = licitacoes.map(lic => {
        const statusClass = lic.status === 'Homologada' ? 'bg-green-100 text-green-700' :
                           lic.status === 'Contratada' ? 'bg-blue-100 text-blue-700' :
                           'bg-yellow-100 text-yellow-700';

        return `
            <div class="flex items-center justify-between p-3 border-b border-gray-100 last:border-0 hover:bg-gray-50 transition">
                <div class="flex-1">
                    <div class="flex items-center space-x-2">
                        <span class="text-sm font-semibold text-blue-600">${lic.numero}</span>
                        <span class="text-xs px-2 py-0.5 rounded-full ${statusClass}">${lic.status}</span>
                    </div>
                    <p class="text-sm text-gray-600 truncate">${lic.objeto}</p>
                </div>
                <div class="text-right">
                    <p class="text-sm font-semibold text-gray-800">${formatCurrency(lic.valor)}</p>
                    <p class="text-xs text-gray-500">${lic.modalidade}</p>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Renderiza os maiores fornecedores
 */
function renderFornecedores() {
    const container = document.getElementById('fornecedores-list');
    if (!container) return;

    const fornecedores = DASHBOARD_DATA.fornecedores;
    const maxValor = Math.max(...fornecedores.map(f => f.valor));

    container.innerHTML = fornecedores.map((forn, index) => {
        const percentage = (forn.valor / maxValor) * 100;

        return `
            <div class="p-3 hover:bg-gray-50 transition rounded-lg">
                <div class="flex items-center justify-between mb-1">
                    <div class="flex items-center space-x-2">
                        <span class="w-6 h-6 flex items-center justify-center bg-blue-100 text-blue-600 rounded-full text-xs font-bold">${index + 1}</span>
                        <span class="text-sm font-medium text-gray-800 truncate max-w-[200px]">${forn.nome}</span>
                    </div>
                    <span class="text-sm font-semibold text-gray-800">${formatCurrency(forn.valor)}</span>
                </div>
                <div class="flex items-center space-x-2 ml-8">
                    <div class="flex-1 bg-gray-200 rounded-full h-2">
                        <div class="bg-blue-600 h-2 rounded-full" style="width: ${percentage}%"></div>
                    </div>
                    <span class="text-xs text-gray-500">${forn.contratos} contratos</span>
                </div>
            </div>
        `;
    }).join('');
}

// ============ FUNÇÕES AUXILIARES ============

function setElementText(id, value) {
    const element = document.getElementById(id);
    if (element) {
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
    return 'R$ ' + value.toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString('pt-BR');
}
