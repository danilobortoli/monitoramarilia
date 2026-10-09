# Mock-ups do portal — Observatório MATRA

Proposta de redesenho do painel, em cinco telas estáticas. Não é o painel em produção.

| Arquivo | Tela |
|---|---|
| `index.html` | Painel do dia |
| `radar.html` | Radar de alertas |
| `fornecedor.html` | Ficha do fornecedor |
| `diario.html` | Diário Oficial |
| `transparencia.html` | Transparência ativa |

## Sobre os dados

Os números vêm de uma coleta feita em 09.10.2026 no Portal da Transparência de Marília
(`transparencia.marilia.sp.gov.br`) e nos dados abertos do site da Prefeitura
(`www.marilia.sp.gov.br/portal/dados-abertos`). O que aparece entre colchetes ainda não foi
calculado. A ficha do fornecedor é descritiva e não aponta irregularidade.

## Sobre o desenho

Sistema Tufte-Bortoli no modo Spiekermann (ET Book e Fira Sans, títulos em itálico, notas à
margem), com o azul institucional da MATRA `#1B67B2` como acento e o marinho `#223463` do logotipo.

As páginas são geradas a partir dos quadros do canvas de design, guardados em
`design/observatorio-canvas/`. Para regerar:

```bash
node design/observatorio-canvas/estatico.js design/observatorio-canvas docs/mockups/observatorio
```

Nesta versão estática os filtros e botões não funcionam; a navegação entre as telas, sim.
