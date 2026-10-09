"""
Coletor do Portal da Transparência da Prefeitura de Marília.

O portal é um SMARAPD PAI (aplicação React). As telas leem uma API JSON
pública no mesmo domínio, sem chave de acesso:

    https://transparencia.marilia.sp.gov.br/paiportalserver/

A API recusa requisições sem os cabeçalhos Origin/Referer do próprio portal
("Não foi possível obter a origem da requisição.").

Endpoints usados:
- GET  MenuPortal                                    árvore de menus (módulos e visões)
- GET  modulovisao/{modulo}/{visao}/configuracao     colunas, periodicidades, chave única
- POST modulovisao/filter                            dados paginados de uma visão

Mapa completo em APIS_MARILIA.md.
"""

import logging
import re
import time
from typing import Any, Dict, Iterator, List, Optional

import requests

logger = logging.getLogger(__name__)


def parse_valor(valor: Any) -> float:
    """Converte '1.234,56' (formato do portal) em 1234.56."""
    if valor is None or valor == "":
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip().replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return 0.0


class PortalMariliaCollector:
    """
    Coletor das visões dinâmicas do Portal da Transparência de Marília.

    Cada visão é identificada por (módulo, visão), como aparece na URL do
    portal: /#/dinamico/{modulo}/{visao}. As mais úteis estão em VISOES.
    """

    PORTAL_URL = "https://transparencia.marilia.sp.gov.br"
    BASE_URL = f"{PORTAL_URL}/paiportalserver"

    # Nome curto -> (módulo, visão). Volumes de referência: exercício 2026,
    # coleta de 09.10.2026.
    VISOES = {
        # Uma linha por liquidação do empenho: o mesmo empenho se repete (34.692 linhas).
        "empenho_analitico": ("fornecedor", "fornecedoranalitico"),
        # Uma linha por empenho, com fornecedor, CPF/CNPJ e valores (22.576).
        "despesas_investimentos": ("DespesaAgrupada", "DespesaseInvestimentos"),
        # Movimentos do empenho (reforço, anulação), com contrato e processo (24.287).
        "movimento_empenho": ("despesas_sinteticas", "MovimentoEmpenho"),
        "despesa_sintetica": ("despesa_sintetica", "DespesaSintetica"),
        "empenho_modalidade": ("quadro_de_renda_local", "EmpenhoModalidade"),
        "restos_a_pagar": ("restoapagar", "restoapagar"),
        "diarias": ("diarias", "diarias"),
        "passagens": ("despesa_viagem", "passagenslocomocao"),
        "subvencoes": ("despesas_subvencoes", "subvencoes"),
        "publicidade": ("despesas_de_pagamentos", "publicidade"),
        "publicidade_digital": ("seguranca", "publicidadedigital"),
        "emendas": ("emendas_parlamentares", "EmendasParlamentares"),
        "receita_analitica": ("folha_pagamento_detalhes", "ReceitaAnalitica"),
        "arrecadacao_mes": ("balancetereceita", "Arrecadacoes"),
        "pagamento_servidores": ("pagamentos", "pagamentoaservidores"),
        "patrimonio": ("patrimonio_mobiliario", "patrimonio"),
        "transferencias_educacao": ("receita_analitica_principal", "transferencias"),
    }

    def __init__(self, timeout: int = 120, por_pagina: int = 5000, pausa: float = 0.5):
        """
        Args:
            timeout: Tempo máximo de espera por requisição
            por_pagina: Registros por página (o servidor aceita ao menos 5.000)
            pausa: Intervalo entre páginas, para não sobrecarregar o portal
        """
        self.timeout = timeout
        self.por_pagina = por_pagina
        self.pausa = pausa
        self.session = requests.Session()
        self.session.headers.update({
            "Origin": self.PORTAL_URL,
            "Referer": f"{self.PORTAL_URL}/",
            "Accept": "application/json",
            "User-Agent": "MonitoraMarilia/2.0 (MATRA - Controle Social)",
        })
        self._configuracoes: Dict[tuple, Dict] = {}

    def _get(self, endpoint: str) -> Any:
        response = self.session.get(f"{self.BASE_URL}/{endpoint}", timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _post(self, endpoint: str, payload: Dict) -> Any:
        response = self.session.post(
            f"{self.BASE_URL}/{endpoint}", json=payload, timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()

    def get_menu(self) -> List[Dict]:
        """Árvore de menus do portal."""
        return self._get("MenuPortal")

    def listar_visoes(self) -> List[Dict]:
        """Visões dinâmicas (dados tabulares) publicadas no menu do portal."""
        visoes = []

        def percorrer(no):
            if isinstance(no, list):
                for item in no:
                    percorrer(item)
            elif isinstance(no, dict):
                # TipoMenuPortal 4 = visão dinâmica (/dinamico/{modulo}/{visao})
                if no.get("TipoMenuPortal") == 4 and no.get("URI", "").startswith("/dinamico/"):
                    _, _, modulo, visao = no["URI"].split("/")[:4]
                    visoes.append({
                        "titulo": no.get("Titulo"),
                        "caminho": no.get("Breadcrumb"),
                        "modulo": modulo,
                        "visao": visao,
                    })
                for valor in no.values():
                    if isinstance(valor, list):
                        percorrer(valor)

        percorrer(self.get_menu())
        return visoes

    def get_configuracao(self, modulo: str, visao: str) -> Dict:
        """Colunas, periodicidades e chave única de uma visão."""
        chave = (modulo, visao)
        if chave not in self._configuracoes:
            self._configuracoes[chave] = self._get(f"modulovisao/{modulo}/{visao}/configuracao")
        return self._configuracoes[chave]

    def _coluna_chave(self, configuracao: Dict) -> str:
        colunas = configuracao.get("VisaoColunas", [])
        chave = next((c for c in colunas if c.get("ChaveUnicaModulo")), None)
        return (chave or colunas[0])["FonteDados"]

    def filtrar(
        self,
        modulo: str,
        visao: str,
        exercicio: int,
        pagina: int = 1,
        por_pagina: Optional[int] = None,
        periodicidade: str = "ANUAL",
        periodo: Optional[str] = None,
        filtros: Optional[List[Dict]] = None,
    ) -> Dict:
        """
        Uma página de uma visão.

        Args:
            periodicidade: ANUAL, MENSAL, BIMESTRAL... (lista em GET periodicidade/periodos)
            periodo: JANEIRO..DEZEMBRO, BIMESTRE1... (None para ANUAL)

        Returns:
            {"QuantidadePaginas": int, "QuantidadeRegistros": int, "Valores": [...]}
        """
        configuracao = self.get_configuracao(modulo, visao)
        payload = {
            "ChaveModulo": modulo,
            "NomeVisao": visao,
            "Filtros": filtros or [],
            "Periodicidade": periodicidade,
            "Periodo": periodo,
            "Exercicio": exercicio,
            "Pagina": pagina,
            "QuantidadeRegistros": por_pagina or self.por_pagina,
            # Ordenar pela chave única deixa a paginação estável entre páginas.
            "Ordenacao": [{
                "ColunaOrdem": self._coluna_chave(configuracao),
                "TipoOrdem": "ascend",
                "Ordem": 1,
            }],
            "FiltroRedirecionaVisao": {"Campo": None, "Valor": None, "TipoValor": None},
        }
        return self._post("modulovisao/filter", payload)

    def iterar(self, modulo: str, visao: str, exercicio: int, **kwargs) -> Iterator[Dict]:
        """Percorre todas as páginas de uma visão."""
        pagina = 1
        while True:
            resultado = self.filtrar(modulo, visao, exercicio, pagina=pagina, **kwargs)
            yield from resultado.get("Valores") or []
            if pagina >= (resultado.get("QuantidadePaginas") or 0):
                break
            pagina += 1
            time.sleep(self.pausa)

    def get_visao(self, nome: str, exercicio: int, **kwargs) -> List[Dict]:
        """
        Todos os registros de uma visão de VISOES no exercício.

        Exemplo: get_visao("diarias", 2026)
        """
        modulo, visao = self.VISOES[nome]
        registros = list(self.iterar(modulo, visao, exercicio, **kwargs))
        logger.info("Portal Marília %s/%s %s: %d registros", modulo, visao, exercicio, len(registros))
        return registros

    def contar(self, nome: str, exercicio: int) -> int:
        """Quantidade de registros de uma visão no exercício, sem baixar os dados."""
        modulo, visao = self.VISOES[nome]
        resultado = self.filtrar(modulo, visao, exercicio, por_pagina=1)
        return resultado.get("QuantidadeRegistros") or 0

    def ultima_data_arquivo(self, modulo: str, visao: str, secao: Optional[str] = None) -> Optional[str]:
        """
        Data mais recente (AAAA-MM-DD) entre os arquivos de uma página fixa do portal.

        As páginas de arquivos (/#/fixo/{modulo}/{visao}) listam documentos numa árvore
        cujos títulos trazem a data, como "07/10/2026". `secao` limita a busca ao ramo
        com esse título (ex.: "MEDICAMENTOS EM FALTA").
        """
        pagina = self._get(f"modulovisao/fixo/{modulo}/{visao}")
        datas = []

        def percorrer(itens, dentro):
            for item in itens or []:
                titulo = item.get("title") or ""
                agora = dentro or (secao is not None and secao.lower() in titulo.lower())
                if agora or secao is None:
                    for d, m, a in re.findall(r"(\d{2})[/.-](\d{2})[/.-](\d{4})", titulo):
                        datas.append(f"{a}-{m}-{d}")
                percorrer(item.get("children"), agora)

        percorrer(pagina.get("VisaoItens"), False)
        return max(datas) if datas else None
