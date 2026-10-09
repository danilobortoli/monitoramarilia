// Converte os quadros .dc.html do canvas em HTML estático (estado inicial), sem o runtime do editor.
const fs = require('fs'), path = require('path'), vm = require('vm');
// Uso: node estatico.js <quadros> <saída> [observatorio.json] [config.json]
// Sem o JSON da coleta, as páginas saem com os dados de exemplo do canvas.
const [src, out, dadosPath, configPath] = process.argv.slice(2);
const dados = dadosPath ? JSON.parse(fs.readFileSync(dadosPath, 'utf8')) : null;
const config = configPath ? JSON.parse(fs.readFileSync(configPath, 'utf8')) : {};
const vincular = dados ? require('./vincular.js') : {};
const dataColeta = dados ? dados.coleta.data.split('-').reverse().join('.') : '09.10.2026';
const NOMES = { 'Main.dc.html': 'index.html', 'Radar.dc.html': 'radar.html', 'Fornecedor.dc.html': 'fornecedor.html', 'Diario.dc.html': 'diario.html', 'Transparencia.dc.html': 'transparencia.html' };
const esc = (v) => String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const busca = (escopo, caminho) => caminho.split('.').reduce((o, k) => (o == null ? undefined : o[k]), escopo);
function preencher(tpl, escopo) {
  tpl = tpl.replace(/\s+on[A-Z][A-Za-z]*="\{\{[^}]*\}\}"/g, '');
  return tpl.replace(/\{\{\s*([\w$.]+)\s*\}\}/g, (m, c) => { const v = busca(escopo, c); return v === undefined || typeof v === 'function' ? '' : esc(v); });
}
function render(tpl, escopo) {
  tpl = tpl.replace(/<sc-for list="\{\{\s*([\w.]+)\s*\}\}" as="(\w+)"[^>]*>([\s\S]*?)<\/sc-for>/g,
    (m, lista, nome, miolo) => (busca(escopo, lista) || []).map((item) => preencher(miolo, { ...escopo, [nome]: item })).join('\n'));
  return preencher(tpl, escopo);
}
const aviso = (destino) => '<div style="box-sizing: border-box; padding: 8px 5%; background: #223463; color: #ffffff; font-family: \'Fira Sans\', -apple-system, \'Segoe UI\', sans-serif; font-size: 12px; letter-spacing: 0.06em; line-height: 1.5">Versão estática · números da coleta de ' + dataColeta + ' · filtros e botões ainda não funcionam' + (dados && destino === 'fornecedor.html' ? ' · a ficha do fornecedor ainda é um exemplo' : '') + '</div>';
for (const [arq, destino] of Object.entries(NOMES)) {
  const h = fs.readFileSync(path.join(src, arq), 'utf8');
  const titulo = h.match(/<title>([\s\S]*?)<\/title>/)[1];
  const helmet = h.match(/<helmet>([\s\S]*?)<\/helmet>/)[1].trim();
  let corpo = h.match(/<\/helmet>([\s\S]*?)<\/x-dc>/)[1].trim();
  const codigo = h.match(/<script type="text\/x-dc"[^>]*>([\s\S]*?)<\/script>/)[1];
  let vals = vm.runInNewContext('class DCLogic { constructor(p) { this.props = p || {}; this.state = {}; } setState() {} }\n' + codigo + '\nnew Component({}).renderVals()');
  const ligar = vincular[arq];
  corpo = render(corpo, ligar ? ligar(vals, dados, config) : vals);
  let pagina = `<!doctype html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>${titulo}</title>\n${helmet}\n</head>\n<body>\n${aviso(destino)}\n${corpo}\n</body>\n</html>\n`;
  for (const [de, para] of Object.entries(NOMES)) pagina = pagina.split(de).join(para);
  pagina = pagina.split('ds/tufte-bortoli/fonts/').join('fonts/');
  if (/\{\{|<sc-|<x-dc|dc\.html/.test(pagina)) throw new Error('sobrou marcação do canvas em ' + destino);
  fs.writeFileSync(path.join(out, destino), pagina);
  console.log(destino, pagina.length, 'bytes');
}
