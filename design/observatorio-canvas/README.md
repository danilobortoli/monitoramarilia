# Observatório MATRA — quadros de design

Fonte das cinco telas publicadas em `docs/` (GitHub Pages):

| Quadro | Página | Tela |
|---|---|---|
| `Main.dc.html` | `index.html` | Painel do dia |
| `Radar.dc.html` | `radar.html` | Radar de alertas |
| `Fornecedor.dc.html` | `fornecedor.html` | Ficha do fornecedor |
| `Diario.dc.html` | `diario.html` | Diário Oficial |
| `Transparencia.dc.html` | `transparencia.html` | Transparência ativa |
| `Boletins.dc.html` | `boletins.html` | Boletins semanais (lista `docs/data/relatorios.json`) |

## Sobre os dados

As páginas publicadas saem dos quadros com os números da última coleta. O workflow diário
roda `python -m src.main observatorio` (que grava `docs/data/observatorio.json`) e depois
regera as páginas:

```bash
node design/observatorio-canvas/estatico.js design/observatorio-canvas docs \
  docs/data/observatorio.json config/observatorio.json
```

`vincular.js` troca, em cada quadro, os valores de exemplo pelos dados do dia: números, datas,
listas e o fato de cada regra do radar. Os textos editoriais (norma, o que falta, notas à margem)
continuam vindo dos quadros. `config/observatorio.json` guarda o que é editado à mão: os casos
acompanhados do painel e as seções sem dado que não se medem automaticamente.

Sem os dois últimos argumentos, o script gera as páginas com os dados de exemplo dos quadros
(coleta de 09.10.2026), como no mock-up original. A ficha do fornecedor ainda é um exemplo fixo.

## Sobre o desenho

Sistema Tufte-Bortoli no modo Spiekermann (ET Book e Fira Sans, títulos em itálico, notas à
margem), com o azul institucional da MATRA `#1B67B2` como acento e o marinho `#223463` do logotipo.

## Interação no navegador

Páginas que precisam de interação têm um script em `interacao/{página}.js`. O gerador o embute
na página junto com os dados que `vincular.js` devolve em `__cliente`. Hoje só o Radar tem script:
clicar numa regra mostra o fato e os registros que ela aponta (até 20 por regra), os filtros por
família funcionam, e `radar.html#2` abre direto no alerta 2. Nas diárias, a lista mostra cargo e
secretaria, sem o nome do servidor.

A busca do Diário e os botões de minuta e de fila ainda não funcionam.
