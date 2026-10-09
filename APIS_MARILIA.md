# APIs da Prefeitura de Marília

Duas fontes públicas, em JSON e sem chave de acesso, alimentam o Observatório. O mapeamento foi
feito em 09.10.2026 a partir do código do front-end do portal, publicado com *source maps*, e de
consultas a cada endpoint. Os volumes abaixo são do exercício de 2026 nessa data.

Coletores: `src/collectors/portal_marilia.py` e `src/collectors/dados_abertos_marilia.py`.

## 1. Portal da Transparência (SMARAPD PAI)

`https://transparencia.marilia.sp.gov.br/#/` é uma aplicação React da SMARAPD. As telas leem a API
em `https://transparencia.marilia.sp.gov.br/paiportalserver/`.

**A API exige os cabeçalhos `Origin` e `Referer` do próprio portal.** Sem eles, responde
`"Não foi possível obter a origem da requisição."`.

| Método | Endpoint | Uso |
|---|---|---|
| GET | `MenuPortal` | Árvore de menus. Itens com `TipoMenuPortal = 4` são visões de dados (`/dinamico/{modulo}/{visao}`); `3` são páginas de arquivos (`/fixo/...`); `2` são links externos. |
| GET | `modulovisao/{modulo}/{visao}/configuracao` | Colunas (`VisaoColunas`: rótulo, campo `FonteDados`, tipo), periodicidades e coluna de chave única. |
| GET | `periodicidade/periodos` | `ANUAL`, `MENSAL` (`JANEIRO`…), `BIMESTRAL` (`BIMESTRE1`…) etc. |
| POST | `modulovisao/filter` | Dados paginados de uma visão (corpo abaixo). |
| GET | `ModuloVisaoItemDetalhe/{modulo}/{visao}/{id}` | Detalhe de um registro. |
| GET | `Modulo/{modulo}/colunasfiltro` · POST `ModuloVisao/filtroavancado` | Busca avançada. |
| POST | `modulovisao/exportar/dinamico/{CSV\|XLSX\|...}` | Exportação (limite de 60.000 linhas no front-end). |
| GET | `DadosAbertos`, `estruturaOrganizacional`, `esic/...`, `glossario`, `faq` | Demais telas. |

Corpo do `modulovisao/filter`:

```json
{
  "ChaveModulo": "diarias", "NomeVisao": "diarias",
  "Exercicio": 2026, "Periodicidade": "ANUAL", "Periodo": null,
  "Pagina": 1, "QuantidadeRegistros": 5000,
  "Ordenacao": [{"ColunaOrdem": "ID", "TipoOrdem": "ascend", "Ordem": 1}],
  "Filtros": [],
  "FiltroRedirecionaVisao": {"Campo": null, "Valor": null, "TipoValor": null}
}
```

A resposta é `{"QuantidadePaginas", "QuantidadeRegistros", "Valores": [...]}`. O servidor aceita
páginas de 5.000 registros, cerca de 4 s cada.

### Visões de dados

| Menu | `modulo/visao` | Nome no coletor | Registros 2026 |
|---|---|---|---:|
| Receitas / Receitas Analíticas | `folha_pagamento_detalhes/ReceitaAnalitica` | `receita_analitica` | 64.895 |
| Receitas / Arrecadações/Mês | `balancetereceita/Arrecadacoes` | `arrecadacao_mes` | 385 |
| Despesas / Despesas Sintéticas | `despesa_sintetica/DespesaSintetica` | `despesa_sintetica` | 17.795 |
| Despesas / Despesas e Investimentos | `DespesaAgrupada/DespesaseInvestimentos` | `despesas_investimentos` | 22.576 |
| Despesas / Passagens e Locomoção | `despesa_viagem/passagenslocomocao` | `passagens` | 499 |
| Despesas / Subvenções | `despesas_subvencoes/subvencoes` | `subvencoes` | 0 |
| Despesas / COVID-19 | `despesa_covid/despesacovid` | — | 0 |
| Despesas / Pagamentos de Restos a Pagar | `restoapagar/restoapagar` | `restos_a_pagar` | 2.345 |
| Despesas / Empenhos / Empenho Analítico | `fornecedor/fornecedoranalitico` | `empenho_analitico` | 34.692 |
| Despesas / Empenhos / Empenho por Modalidade | `quadro_de_renda_local/EmpenhoModalidade` | `empenho_modalidade` | 9 |
| Despesas / Empenhos / Movimento do Empenho | `despesas_sinteticas/MovimentoEmpenho` | `movimento_empenho` | 24.287 |
| Despesas / Publicidade e Propaganda | `despesas_de_pagamentos/publicidade` | `publicidade` | 3 |
| Despesas / Publicidade Digital (Lei 8.578/2020) | `seguranca/publicidadedigital` | `publicidade_digital` | 335 |
| Diárias | `diarias/diarias` | `diarias` | 4.537 |
| Contratos / Patrimônio | `patrimonio_mobiliario/patrimonio` | `patrimonio` | 153.211 |
| Emendas Parlamentares / Despesas com Emendas | `emendas_parlamentares/EmendasParlamentares` | `emendas` | 131 |
| Recursos Humanos / Pagamentos a Servidores e Estagiários | `pagamentos/pagamentoaservidores` | `pagamento_servidores` | 52.456 |
| Educação / Transferências / Remanejamentos | `receita_analitica_principal/transferencias` | `transferencias_educacao` | 2.012 |

### Cuidados com os dados do portal

- **Empenho Analítico repete o empenho a cada liquidação**, às vezes com linhas duplicadas. As
  34.692 linhas de 2026 não são 34.692 empenhos. Para somar por fornecedor, use
  **Despesas e Investimentos**: uma linha por empenho ou anulação, com CPF/CNPJ.
- Em Despesas e Investimentos, `TipEmpenho` distingue `Empenho` (20.839) de
  `Anulação de Empenho` (1.737), que já vem com **valor negativo**. A visão inclui a Câmara
  (`UG = CÂMARA MUNICIPAL DE MARÍLIA`).
- Valores monetários vêm como texto no formato `1.234,56` (use `parse_valor`). Datas vêm em
  vários formatos (`30/09/2026 00:00`, `2026-08-24`, `Aug 24 2026  2:00PM`).
- Textos vêm com espaços à direita (campos de largura fixa).
- Há `NroEmpenho = 999999999` em algumas linhas, aparentemente um marcador do sistema.

## 2. Dados abertos do site da Prefeitura

`https://www.marilia.sp.gov.br/portal/dados-abertos/{conjunto}/{ano}` devolve `{"dados": [...]}`.
Um conjunto vazio vem como `{"dados": ["Nenhum registro encontrado."]}`.

| Conjunto | Registros 2026 | Campos principais |
|---|---:|---|
| `compra-direta` | 673 | `titulo`, `modalidade` (Dispensa, Inexigibilidade, Adesão a ARP), `situacao`, `numeroProcesso`, `dataPostagem`, `valorEstimado`, `valorHomologado`, `descricao` |
| `contratos` | 1.151 | `nomeContratada`, `numeroContrato`, `numeroProcesso`, `tipo`, `tipoLicitacao`, `valorContrato`, `dataAssinatura`, `dataInicioVigencia`, `dataFimVigencia`, `situacao` |
| `licitacoes` | 163 | os mesmos de `compra-direta` |
| `chamamento-publico` | 1 | os mesmos de `compra-direta` |
| `obras` | 38 | `titulo`, `categoria`, `situacao`, `valor`, `dataExecucaoInicio`, `dataExecucaoFim`, `descricao` (contrato, contratada, processo) |
| `diario-oficial` | 196 | `edicao`, `data`, `edicaoExtra`, `descricao` (texto integral, sem paginação; cerca de 7 MB no ano) |
| `legislacao` | 2.578 | `numero`, `categoria`, `ementa`, `data`, `situacao` |
| `sic`, `ouvidoria` | objeto | totais de pedidos (zerados em 2026; o atendimento corre no 1Doc) |
| `avaliacoes` | objeto | totais de avaliações dos serviços |
| `contas-publicas`, `relatorio-viagens`, `concursos` | 0 | vazios em 2026 |
| `audiencias-publicas`, `carta-servicos` | 1 | registros de teste |

`descricao` vem com entidades HTML (`&ccedil;`, `<br />`); o coletor as decodifica.

## Radar do Observatório

`python -m src.main observatorio --ano 2026` coleta as duas fontes e grava
`docs/data/observatorio.json` com os totais do painel, as oito regras do radar
(`src/analyzers/radar.py`) e os dados das demais páginas (`src/analyzers/paineis.py`). Leva
cerca de 40 s com o cache de fornecedores em dia. Resultado de 09.10.2026:

| # | Regra | Base | Resultado |
|---|---|---|---:|
| 1 | Nova dispensa ou inexigibilidade (situação "Aberto") | 673 compras diretas | 58 |
| 2 | Contrato ou ata sem nome da contratada | 1.151 contratos | 473 |
| 3 | Licitação sem valor estimado | 163 licitações | 163 |
| 4 | Justificativa de quebra da ordem cronológica (art. 141, §1º, Lei 14.133/2021) | 196 edições | 105 |
| 5 | Fornecedor sem empenho em 2024–2025 e com empenhado ≥ R$ 100 mil em 2026 | 1.974 fornecedores | 53 |
| 6 | Diárias acima de Q3 + 3·IQR dos colegas do mesmo cargo (cargos com 5 ou mais beneficiários) | 4.537 registros | 1 |
| 7 | Obra cancelada ou paralisada | 38 obras | 7 |
| 8 | Contrato vigente que termina em até 60 dias | 1.040 vigentes | 71 |

Os itens de cada regra são registros que pedem leitura, não constatação de irregularidade. CPFs
de pessoas físicas saem mascarados (`***.456.789-**`).

## Histórico entre coletas

O portal só mostra o estado atual. Para saber o que apareceu, mudou ou sumiu, cada coleta grava em
`historico/` (`src/analyzers/acervo.py`):

| Arquivo | Conteúdo |
|---|---|
| `estado/{compra-direta,contratos,licitacoes,obras}.json` | Registros da coleta, em ordem estável |
| `estado/diario-oficial.json` | Número, data e impressão digital do texto de cada edição |
| `estado/despesas.json` | IDs dos lançamentos de Despesas e Investimentos |
| `mudancas/AAAA-MM-DD.json` | Novos, alterados (com os campos que mudaram) e removidos |
| `radar.jsonl` | Uma linha por coleta: totais e resultado de cada regra |
| `cache/fornecedores_conhecidos.json` | Fornecedores dos dois anos anteriores, renovado a cada 30 dias |

Os arquivos de estado são sobrescritos a cada coleta; as versões anteriores ficam no histórico do
git. Os conjuntos não têm chave única (há registros repetidos por completo), por isso a comparação
usa uma impressão digital do conteúdo de cada registro, sem `dataAtualizacao`. Uma saída e uma
entrada com o mesmo tipo, número e processo contam como alteração.

O cache guarda CNPJs por extenso. De CPFs, guarda só os seis dígitos que a máscara deixa à vista,
junto com o nome normalizado. Dados brutos de despesas não entram no repositório: os anos
anteriores podem ser recoletados no portal quando for preciso (`--renovar-cache`).
