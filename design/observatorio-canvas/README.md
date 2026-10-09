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

Os números vêm de uma coleta feita em 09.10.2026 no Portal da Transparência de Marília
(`transparencia.marilia.sp.gov.br`) e nos dados abertos do site da Prefeitura
(`www.marilia.sp.gov.br/portal/dados-abertos`). O que aparece entre colchetes ainda não foi
calculado. A ficha do fornecedor é descritiva e não aponta irregularidade.

## Sobre o desenho

Sistema Tufte-Bortoli no modo Spiekermann (ET Book e Fira Sans, títulos em itálico, notas à
margem), com o azul institucional da MATRA `#1B67B2` como acento e o marinho `#223463` do logotipo.

Para regerar as páginas a partir dos quadros:

```bash
node design/observatorio-canvas/estatico.js design/observatorio-canvas docs
```

Nesta versão estática os filtros e botões não funcionam; a navegação entre as telas, sim.
