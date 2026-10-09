# Observatório MATRA — quadros de design

Fonte das cinco telas publicadas em `docs/` (GitHub Pages):

| Quadro | Página | Tela |
|---|---|---|
| `Main.dc.html` | `index.html` | Painel do dia |
| `Radar.dc.html` | `radar.html` | Radar de alertas |
| `Fornecedor.dc.html` | `fornecedor.html` | Ficha do fornecedor |
| `Diario.dc.html` | `diario.html` | Diário Oficial |
| `Transparencia.dc.html` | `transparencia.html` | Transparência ativa |

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

Nesta versão estática os filtros e botões não funcionam; a navegação entre as telas, sim.
