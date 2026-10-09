// Radar: troca o alerta selecionado, filtra por família e lista os registros de cada regra.
// Os dados vêm do JSON que o gerador estático embute na página (#dados-pagina).
(function () {
  var dados = JSON.parse(document.getElementById('dados-pagina').textContent);
  var regras = {};
  dados.regras.forEach(function (r) { regras[r.n] = r; });

  var botoes = Array.prototype.slice.call(document.querySelectorAll('[data-regra]'));
  var filtros = Array.prototype.slice.call(document.querySelectorAll('[data-filtro]'));
  var alerta = document.getElementById('alerta');
  var campo = function (nome) { return alerta.querySelector('[data-campo="' + nome + '"]'); };

  var rotulo = 'margin: 0 0 2px; font-family: \'Fira Sans\', -apple-system, \'Segoe UI\', sans-serif; font-size: 11px; font-weight: 500; letter-spacing: 0.1em; text-transform: uppercase; color: #666666';

  function el(tag, estilo, texto) {
    var e = document.createElement(tag);
    if (estilo) e.setAttribute('style', estilo);
    if (texto) e.textContent = texto;
    return e;
  }

  function mostrarItens(r) {
    var caixa = campo('itens');
    caixa.textContent = '';
    if (!r.itens.length) return;
    var n = r.itens.length;
    caixa.appendChild(el('p', rotulo, n < r.total ? 'Registros · ' + n + ' de ' + r.total.toLocaleString('pt-BR') : 'Registros · ' + n));
    var lista = el('ol', 'margin: 6px 0 26px; padding: 0; list-style: none');
    r.itens.forEach(function (i) {
      var li = el('li', 'padding: 10px 0; border-top: 1px solid #e3e3e3');
      li.appendChild(el('span', 'display: block; font-size: 16px; line-height: 1.4; color: #111111', i.titulo));
      li.appendChild(el('span', 'display: block; font-style: italic; font-size: 14px; line-height: 1.4; color: #666666', i.detalhe));
      lista.appendChild(li);
    });
    caixa.appendChild(lista);
  }

  function selecionar(n, rolar) {
    var r = regras[n];
    if (!r) return;
    botoes.forEach(function (b) {
      var ativo = b.getAttribute('data-regra') === n;
      b.setAttribute('aria-pressed', ativo ? 'true' : 'false');
      b.style.background = ativo ? '#eef1f5' : '#ffffff';
    });
    campo('rotulo').textContent = 'Alerta ' + r.n + ' · ' + r.familia;
    campo('regra').textContent = r.regra;
    campo('norma').textContent = r.norma;
    campo('fato').textContent = r.fato;
    campo('falta').textContent = r.falta;
    mostrarItens(r);
    if (history.replaceState) history.replaceState(null, '', '#' + n);
    // No celular o alerta fica abaixo da lista: leva o leitor até ele.
    if (rolar && alerta.getBoundingClientRect().top > window.innerHeight * 0.6) {
      alerta.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }

  function filtrar(familia) {
    filtros.forEach(function (f) {
      var ativo = f.getAttribute('data-filtro') === familia;
      f.setAttribute('aria-pressed', ativo ? 'true' : 'false');
      f.style.color = ativo ? '#111111' : '#1b67b2';
      f.style.borderBottomColor = ativo ? '#111111' : '#ffffff';
    });
    var primeira = null;
    botoes.forEach(function (b) {
      var visivel = familia === 'Todas' || b.getAttribute('data-familia') === familia;
      b.style.display = visivel ? 'flex' : 'none';
      if (visivel && !primeira) primeira = b.getAttribute('data-regra');
    });
    var atual = botoes.filter(function (b) { return b.getAttribute('aria-pressed') === 'true' && b.style.display !== 'none'; })[0];
    if (!atual && primeira) selecionar(primeira, false);
  }

  botoes.forEach(function (b) {
    b.addEventListener('click', function () { selecionar(b.getAttribute('data-regra'), true); });
  });
  filtros.forEach(function (f) {
    f.addEventListener('click', function () { filtrar(f.getAttribute('data-filtro')); });
  });

  // Abre no alerta pedido pelo endereço (radar.html#2), ou no que já vem marcado.
  var pedido = (location.hash || '').replace('#', '');
  var marcado = botoes.filter(function (b) { return b.getAttribute('aria-pressed') === 'true'; })[0];
  selecionar(regras[pedido] ? pedido : (marcado ? marcado.getAttribute('data-regra') : dados.regras[0].n), false);
})();
