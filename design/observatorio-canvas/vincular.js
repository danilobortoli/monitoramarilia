// Liga os quadros do canvas aos dados da coleta (docs/data/observatorio.json).
// Cada função recebe os valores de exemplo do quadro e devolve os mesmos campos com os
// números do dia. Textos editoriais (norma, "o que falta") continuam vindo do canvas.

const fmtNumero = new Intl.NumberFormat('pt-BR');
const fmtPct = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];

const numero = (n) => fmtNumero.format(n);
const dataUTC = (iso) => new Date(iso.slice(0, 10) + 'T12:00:00Z');
const dataBR = (iso) => (iso ? iso.slice(0, 10).split('-').reverse().join('.') : '');
const dataExtenso = (iso) => { const d = dataUTC(iso); return `${d.getUTCDate()} de ${MESES[d.getUTCMonth()]} de ${d.getUTCFullYear()}`; };
const diaSemana = (iso) => new Intl.DateTimeFormat('pt-BR', { weekday: 'long', timeZone: 'UTC' }).format(dataUTC(iso));
const bilhoes = (v) => (v >= 1e9 ? `R$ ${fmtNumero.format(Math.round(v / 1e7) / 100)} bi` : `R$ ${fmtNumero.format(Math.round(v / 1e4) / 100)} mi`);
const plural = (n, um, varios) => `${numero(n)} ${n === 1 ? um : varios}`;

const POR_EXTENSO = ['Nenhum', 'Um', 'Dois', 'Três', 'Quatro', 'Cinco'];

const UNIDADE_BASE = { quebra_ordem_cronologica: 'edições', obra_parada_ou_cancelada: 'obras' };

function Main(vals, d, config) {
  const t = d.totais;
  const ano = d.exercicio;
  const coleta = d.coleta.data;
  const serie = d.serie_contratacao_direta || [];
  const maior = Math.max(...serie.map((s) => s.pct_direta), 1);
  const atual = serie.find((s) => s.ano === ano);
  const mesColeta = MESES[dataUTC(coleta).getUTCMonth()];
  return {
    ...vals,
    numeros: [
      { valor: numero(t.empenhos), rotulo: `Empenhos em ${ano}`, nota: `${bilhoes(t.empenhado_liquido)} empenhados, já descontadas ${numero(t.anulacoes)} anulações` },
      { valor: numero(t.compras_diretas), rotulo: 'Compras diretas', nota: `${numero(t.dispensas)} dispensas e ${numero(t.inexigibilidades)} inexigibilidades` },
      { valor: numero(t.licitacoes_abertas), rotulo: 'Licitações abertas', nota: `de ${numero(t.licitacoes)} publicadas no ano` },
      { valor: numero(t.contratos_vigentes), rotulo: 'Contratos vigentes', nota: `de ${numero(t.contratos)} registrados` },
      { valor: numero(t.obras_em_andamento), rotulo: 'Obras em andamento', nota: `${numero(t.obras_canceladas)} canceladas, ${numero(t.obras_concluidas)} concluídas` },
    ],
    novidades: d.novidades.itens.map((i) => ({ ...i })),
    serie: serie.map((s) => ({
      ano: String(s.ano),
      valor: fmtPct.format(s.pct_direta) + '%',
      largura: Math.round((100 * s.pct_direta) / maior) + '%',
      cor: s.ano === ano ? '#1b67b2' : '#222222',
    })),
    casos: (config.casos || []).map((texto) => ({ texto })),
    txt: {
      ...vals.txt,
      novidades_titulo: d.novidades.itens.length === 0
        ? 'Nenhum registro novo desde a coleta anterior'
        : `${POR_EXTENSO[d.novidades.itens.length]} ${d.novidades.itens.length === 1 ? 'registro que pede' : 'registros que pedem'} leitura`,
      data_extenso: `${diaSemana(coleta)}, ${dataExtenso(coleta)}`,
      lead: d.novidades.resumo,
      nota_serie: atual
        ? `Dispensa e inexigibilidade somadas, sobre o total empenhado. O ano de ${ano} vai até ${mesColeta}, e ${Math.round(atual.pct_sem_modalidade)}% do empenhado não traz modalidade informada.`
        : 'Dispensa e inexigibilidade somadas, sobre o total empenhado.',
      medicamentos: d.saude.medicamentos_em_falta ? `Medicamentos em falta: lista de ${dataBR(d.saude.medicamentos_em_falta)}.` : 'Medicamentos em falta: lista indisponível nesta coleta.',
      leitos: d.saude.fila_de_leitos ? `Fila de leitos nas UPAs: lista de ${dataBR(d.saude.fila_de_leitos)}.` : 'Fila de leitos nas UPAs: lista indisponível nesta coleta.',
      estado_coleta: `${d.coleta.visoes_portal.responderam} de ${d.coleta.visoes_portal.total} visões do portal responderam em ${dataBR(coleta)}. Diário Oficial coletado até a edição ${d.diario.ultima_edicao}.`,
    },
  };
}

function Radar(vals, d) {
  const porNumero = Object.fromEntries(d.regras.map((r) => [String(r.n), r]));
  const ligar = (item) => {
    const r = porNumero[item.n];
    if (!r) return item;
    const base = typeof r.base === 'number' ? `${numero(r.base)} ${UNIDADE_BASE[r.id] || 'registros'}` : r.base;
    return { ...item, regra: r.regra, fonte: r.fonte, base, resultado: `${numero(r.resultado)} ${r.unidade}`, fato: r.fato || item.fato };
  };
  return {
    ...vals,
    regras: vals.regras.map(ligar),
    sel: ligar(vals.sel),
    txt: { ...vals.txt, exercicio: String(d.exercicio), coleta: dataBR(d.coleta.data) },
  };
}

function Diario(vals, d) {
  const di = d.diario;
  const ano = d.exercicio;
  const coleta = d.coleta.data;
  const mesInicio = MESES[dataUTC(di.primeira_data).getUTCMonth()];
  const ultimoMes = di.meses[di.meses.length - 1];
  const fimColeta = dataUTC(di.ultima_data);
  const tr = di.trecho;
  return {
    ...vals,
    busca: di.frase,
    faixa: di.faixa.map((b) => ({ h: b ? '24px' : '9px', cor: b ? '#223463' : '#c4c9d1' })),
    meses: di.meses.map((m) => ({ mes: m.mes, valor: `${m.com} de ${m.total}`, largura: Math.round((100 * m.com) / m.total) + '%' })),
    edicoes: di.recentes.map((e) => ({
      n: e.edicao + (e.extra ? ' (extra)' : ''),
      data: dataBR(e.data),
      chars: numero(e.caracteres),
      cnpjs: numero(e.cnpjs),
      disp: numero(e.dispensa),
      port: numero(e.portarias),
      quebra: e.frase ? 'Sim' : 'Não',
      cor: e.frase ? '#111111' : '#6b6b6b',
    })),
    txt: {
      ...vals.txt,
      contagem: `${plural(di.edicoes, 'edição', 'edições')} em ${ano}, ${di.extras === 0 ? 'nenhuma extra' : di.extras === 1 ? 'uma delas extra' : numero(di.extras) + ' delas extras'}`,
      titulo: `A mesma justificativa, em ${numero(di.com_frase)} de ${numero(di.edicoes)} edições`,
      faixa_aria: `Faixa com as ${numero(di.edicoes)} edições de ${ano}, da nº ${di.primeira_edicao} à nº ${di.ultima_edicao}; ${numero(di.com_frase)} delas trazem a frase procurada`,
      faixa_inicio: `nº ${di.primeira_edicao} · ${mesInicio}`,
      faixa_fim: `nº ${di.ultima_edicao} · ${fimColeta.getUTCDate()} de ${MESES[fimColeta.getUTCMonth()]}`,
      trecho_titulo: tr ? `Edição ${tr.edicao}, de ${dataExtenso(tr.data)}` : 'Nenhuma edição com a frase',
      trecho_antes: tr ? tr.antes : '',
      trecho_frase: tr ? tr.frase + '.' : '',
      trecho_depois: tr ? tr.depois.replace(/^\.\s*/, '') : '',
      trecho_seguinte: tr ? tr.seguinte : '',
      edicao_link: 'https://www.marilia.sp.gov.br/portal/diario-oficial',
      edicao_rotulo: 'Abrir o Diário Oficial no site da Prefeitura',
      recentes_titulo: `O que trazem as ${numero(di.recentes.length)} edições mais recentes`,
      nota_meses: `Edições com a frase sobre o total do mês. ${MESES[fimColeta.getUTCMonth()].replace(/^./, (c) => c.toUpperCase())} vai até o dia ${fimColeta.getUTCDate()}.`,
      exercicio: String(ano),
      coleta: dataBR(coleta),
    },
  };
}

function Transparencia(vals, d, config) {
  const tp = d.transparencia;
  const t = d.totais;
  const campos = tp.campos.slice(0, 8);
  const secoes = [...tp.secoes, ...(config.secoes_manuais || [])];
  const cheios = tp.campos.filter((c) => c.pct === 100).length;
  const semNome = (d.regras.find((r) => r.id === 'contrato_sem_contratada') || { resultado: 0 }).resultado;
  const hist = d.historico || [];
  let serieIndice = 'A série histórica do índice começa na segunda coleta.';
  if (hist.length >= 2) {
    const [a, b] = [hist[hist.length - 2], hist[hist.length - 1]];
    serieIndice = `Contratos sem contratada: ${numero(a.radar.contrato_sem_contratada)} em ${dataBR(a.data)} e ${numero(b.radar.contrato_sem_contratada)} em ${dataBR(b.data)}.`;
  }
  return {
    ...vals,
    numeros: [
      { valor: numero(cheios), rotulo: 'Campos 100% vazios', nota: 'em todos os registros do ano' },
      { valor: numero(semNome), rotulo: 'Contratos sem contratada', nota: `${Math.round((100 * semNome) / t.contratos)}% dos ${numero(t.contratos)} de ${d.exercicio}` },
      { valor: numero(secoes.length), rotulo: 'Seções sem dado', nota: 'no menu, sem conteúdo utilizável' },
      { valor: `${d.coleta.visoes_portal.responderam} de ${d.coleta.visoes_portal.total}`, rotulo: 'Visões em dia', nota: `responderam em ${dataBR(d.coleta.data)}` },
    ],
    campos: campos.map((c) => ({ conjunto: c.conjunto, campo: c.campo, pct: c.pct + '%', largura: c.pct + '%', vazios: `${numero(c.vazios)} de ${numero(c.total)}` })),
    secoes,
    txt: {
      ...vals.txt,
      exercicio: String(d.exercicio),
      coleta: dataBR(d.coleta.data),
      providencia: `Um pedido único reúne as ${numero(campos.length)} lacunas de campo e as ${numero(secoes.length)} seções sem dado, com a contagem de cada uma.`,
      serie_indice: serieIndice,
    },
  };
}

module.exports = { 'Main.dc.html': Main, 'Radar.dc.html': Radar, 'Diario.dc.html': Diario, 'Transparencia.dc.html': Transparencia };
