# MonitoraMarília

Sistema de monitoramento e análise do Portal de Transparência do Município de Marília, desenvolvido pela **MATRA - Marília Transparente**.

## 🎯 Objetivo

Ferramenta de controle social para:
- Monitorar a conformidade do Portal de Transparência com a LAI (Lei 12.527/2011)
- Coletar e analisar dados públicos automaticamente
- Detectar inconsistências e anomalias em gastos públicos
- Gerar relatórios para subsidiar ações de controle social

## 📋 Funcionalidades

### 1. Coleta Automatizada
- Scraping do Portal de Transparência de Marília
- Coleta de licitações, contratos, despesas, receitas e folha de pagamento
- Armazenamento histórico para análise temporal

### 2. Análise de Conformidade LAI
- Verificação dos requisitos obrigatórios da Lei 12.527/2011
- Checklist automático de transparência ativa
- Monitoramento de prazos de atualização

### 3. Detecção de Anomalias
- Identificação de valores atípicos em despesas
- Alertas sobre contratos sem licitação
- Análise de fornecedores recorrentes
- Detecção de fracionamento de despesas

### 4. Geração de Relatórios
- Relatórios de conformidade para representações ao MP
- Análises comparativas entre períodos
- Exportação em PDF/Excel para ações judiciais

## 🛠️ Tecnologias

- **Python 3.11+**
- **SQLite/PostgreSQL** - Armazenamento de dados
- **Scrapy/BeautifulSoup** - Coleta de dados web
- **Pandas** - Análise de dados
- **FastAPI** - API REST (opcional)
- **Rich** - Interface CLI

## 📁 Estrutura do Projeto

```
monitoramarilia/
├── src/
│   ├── collectors/      # Módulos de coleta de dados
│   ├── analyzers/       # Analisadores de conformidade e anomalias
│   ├── reporters/       # Geradores de relatórios
│   ├── database/        # Modelos e conexão com banco
│   ├── alerts/          # Sistema de alertas
│   └── utils/           # Utilitários comuns
├── data/                # Dados coletados
├── reports/             # Relatórios gerados
├── tests/               # Testes automatizados
├── config/              # Configurações
└── docs/                # Documentação adicional
```

## 🚀 Instalação

```bash
# Clonar o repositório
git clone https://github.com/danilobortoli/monitoramarilia.git
cd monitoramarilia

# Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar
cp config/config.example.yaml config/config.yaml
```

## 💻 Uso

```bash
# Verificar conformidade LAI do portal
python -m src.main check-lai

# Coletar dados de licitações
python -m src.main collect --type licitacoes --periodo 2024

# Analisar anomalias em despesas
python -m src.main analyze --type despesas --threshold 2.0

# Gerar relatório completo
python -m src.main report --output reports/relatorio_mensal.pdf
```

## 📊 Indicadores Monitorados

| Categoria | Dados Coletados |
|-----------|-----------------|
| Licitações | Modalidade, valor, participantes, vencedor |
| Contratos | Objeto, valor, vigência, aditivos |
| Despesas | Empenho, liquidação, pagamento, favorecido |
| Receitas | Arrecadação por fonte e período |
| Pessoal | Folha de pagamento, cargos, remuneração |
| Diárias/Viagens | Beneficiário, destino, valor, justificativa |

## ⚖️ Base Legal

- **Lei 12.527/2011** - Lei de Acesso à Informação (LAI)
- **Lei Complementar 131/2009** - Lei da Transparência
- **Decreto 7.724/2012** - Regulamenta a LAI no Executivo Federal
- **Lei 14.129/2021** - Governo Digital

## 🤝 Contribuição

Este é um projeto de controle social. Contribuições são bem-vindas!

## 📄 Licença

MIT License - Uso livre para fins de controle social e transparência pública.

## 📞 Contato

**MATRA - Marília Transparente**
- OSCIP de controle social do município de Marília/SP
