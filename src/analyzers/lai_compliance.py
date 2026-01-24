"""
Analisador de Conformidade com a Lei de Acesso à Informação (LAI).
Verifica se o Portal de Transparência atende aos requisitos da Lei 12.527/2011.

Usa Playwright para verificar páginas JavaScript (SMARAPD).
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import logging

# Tentar importar playwright
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ComplianceStatus(Enum):
    """Status de conformidade de um item."""
    CONFORME = "ok"
    ATENCAO = "warning"
    IRREGULAR = "error"
    NAO_VERIFICADO = "pending"


@dataclass
class LAIItem:
    """Representa um item do checklist LAI."""
    id: int
    nome: str
    descricao: str
    artigo: str
    url_path: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    status: ComplianceStatus = ComplianceStatus.NAO_VERIFICADO
    observacao: str = ""
    verificado_em: Optional[str] = None


class LAIComplianceAnalyzer:
    """
    Analisador de conformidade com a LAI (Lei 12.527/2011).
    Verifica os itens obrigatórios de transparência ativa (Art. 8º, §1º).

    Usa Playwright para acessar páginas JavaScript do portal SMARAPD.
    """

    BASE_URL = "https://transparencia.marilia.sp.gov.br"

    # Checklist baseado no Art. 8º, §1º da Lei 12.527/2011
    # Inclui palavras-chave para verificar conteúdo
    CHECKLIST_LAI = [
        LAIItem(
            id=1,
            nome="Estrutura organizacional",
            descricao="Registro das competências e estrutura organizacional",
            artigo="Art. 8º, §1º, I",
            url_path="/#/estrutura",
            keywords=["estrutura", "organograma", "secretaria", "órgão"]
        ),
        LAIItem(
            id=2,
            nome="Competências e atribuições",
            descricao="Competências e atribuições dos órgãos e entidades",
            artigo="Art. 8º, §1º, I",
            url_path="/#/competencias",
            keywords=["competência", "atribuição", "função"]
        ),
        LAIItem(
            id=3,
            nome="Endereços e telefones",
            descricao="Endereços e telefones das unidades",
            artigo="Art. 8º, §1º, I",
            url_path="/#/contato",
            keywords=["endereço", "telefone", "contato", "e-mail"]
        ),
        LAIItem(
            id=4,
            nome="Horários de atendimento",
            descricao="Horários de atendimento ao público",
            artigo="Art. 8º, §1º, I",
            url_path="/#/atendimento",
            keywords=["horário", "atendimento", "funcionamento"]
        ),
        LAIItem(
            id=5,
            nome="Repasses e transferências",
            descricao="Registros de quaisquer repasses ou transferências de recursos financeiros",
            artigo="Art. 8º, §1º, II",
            url_path="/#/transferencia",
            keywords=["repasse", "transferência", "convênio", "recurso"]
        ),
        LAIItem(
            id=6,
            nome="Despesas",
            descricao="Registros das despesas (execução orçamentária e financeira detalhada)",
            artigo="Art. 8º, §1º, III",
            url_path="/#/despesa",
            keywords=["despesa", "empenho", "pagamento", "liquidação"]
        ),
        LAIItem(
            id=7,
            nome="Licitações e contratos",
            descricao="Informações de procedimentos licitatórios e contratos celebrados",
            artigo="Art. 8º, §1º, IV",
            url_path="/#/licitacao",
            keywords=["licitação", "pregão", "contrato", "edital"]
        ),
        LAIItem(
            id=8,
            nome="Receitas",
            descricao="Dados gerais para acompanhamento de programas e obras",
            artigo="Art. 8º, §1º, V",
            url_path="/#/receita",
            keywords=["receita", "arrecadação", "tributo"]
        ),
        LAIItem(
            id=9,
            nome="Perguntas frequentes",
            descricao="Respostas a perguntas mais frequentes da sociedade",
            artigo="Art. 8º, §1º, VI",
            url_path="/#/faq",
            keywords=["pergunta", "faq", "dúvida", "frequente"]
        ),
        LAIItem(
            id=10,
            nome="Ferramenta de pesquisa",
            descricao="Ferramenta de pesquisa de conteúdo",
            artigo="Art. 8º, §3º, I",
            url_path=None,  # Verificar na página principal
            keywords=["pesquisa", "busca", "buscar", "pesquisar"]
        ),
        LAIItem(
            id=11,
            nome="Dados em formatos abertos",
            descricao="Possibilidade de download em formatos abertos (CSV, XLS)",
            artigo="Art. 8º, §3º, II",
            url_path=None,  # Verificar em várias páginas
            keywords=["csv", "excel", "xls", "download", "exportar"]
        ),
        LAIItem(
            id=12,
            nome="Relatório estatístico LAI",
            descricao="Relatório estatístico de pedidos de informação",
            artigo="Art. 30, III",
            url_path="/#/relatorio-lai",
            keywords=["relatório", "estatística", "lai", "pedido", "informação"]
        ),
    ]

    def __init__(self, timeout: int = 60, headless: bool = True):
        """
        Inicializa o analisador.

        Args:
            timeout: Tempo máximo de espera por página (segundos)
            headless: Executar navegador sem interface gráfica
        """
        self.timeout = timeout
        self.headless = headless
        self.results: List[LAIItem] = []
        self._browser = None
        self._playwright = None

    async def _init_browser(self):
        """Inicializa o navegador Playwright."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError(
                "Playwright não está instalado. "
                "Execute: pip install playwright && playwright install chromium"
            )

        if self._browser is None:
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless
            )
            logger.info("Navegador Playwright inicializado para verificação LAI")

    async def _close_browser(self):
        """Fecha o navegador."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def _check_page_content(
        self,
        url: str,
        keywords: List[str],
        wait_time: int = 5
    ) -> tuple[bool, str, bool]:
        """
        Verifica se uma página contém conteúdo esperado usando Playwright.

        Args:
            url: URL completa da página
            keywords: Palavras-chave esperadas
            wait_time: Tempo de espera para carregar JavaScript

        Returns:
            Tupla (acessível, conteúdo_encontrado, observação)
        """
        await self._init_browser()

        try:
            page = await self._browser.new_page()
            page.set_default_timeout(self.timeout * 1000)

            logger.info(f"Verificando: {url}")
            response = await page.goto(url, wait_until="networkidle")

            if response is None or response.status >= 400:
                await page.close()
                return False, "Página não acessível", False

            # Aguardar carregamento JavaScript
            await asyncio.sleep(wait_time)

            # Obter conteúdo da página
            content = await page.content()
            text_content = await page.evaluate("() => document.body.innerText")
            text_lower = text_content.lower() if text_content else ""

            await page.close()

            # Verificar se contém alguma das palavras-chave
            if keywords:
                found = any(kw.lower() in text_lower for kw in keywords)
                if found:
                    return True, "Conteúdo disponível", True
                else:
                    return True, "Página acessível, mas conteúdo não confirmado", False
            else:
                # Apenas verificar se a página carregou
                has_content = len(text_lower) > 100
                return True, "Página acessível", has_content

        except Exception as e:
            logger.warning(f"Erro ao verificar {url}: {e}")
            return False, f"Erro: {str(e)[:50]}", False

    async def run_compliance_check(self) -> Dict[str, Any]:
        """
        Executa a verificação completa de conformidade LAI.

        Returns:
            Dicionário com resultados da verificação
        """
        logger.info("Iniciando verificação de conformidade LAI...")

        self.results = []
        agora = datetime.now().isoformat()

        try:
            await self._init_browser()

            for item in self.CHECKLIST_LAI:
                logger.info(f"Verificando: {item.nome}")

                item_result = LAIItem(
                    id=item.id,
                    nome=item.nome,
                    descricao=item.descricao,
                    artigo=item.artigo,
                    url_path=item.url_path,
                    keywords=item.keywords,
                    verificado_em=agora
                )

                if item.url_path:
                    full_url = f"{self.BASE_URL}{item.url_path}"
                    accessible, obs, content_found = await self._check_page_content(
                        full_url,
                        item.keywords
                    )

                    if accessible and content_found:
                        item_result.status = ComplianceStatus.CONFORME
                        item_result.observacao = obs
                    elif accessible:
                        item_result.status = ComplianceStatus.ATENCAO
                        item_result.observacao = obs
                    else:
                        item_result.status = ComplianceStatus.IRREGULAR
                        item_result.observacao = obs
                else:
                    # Verificar na página principal
                    main_url = self.BASE_URL
                    accessible, obs, content_found = await self._check_page_content(
                        main_url,
                        item.keywords
                    )

                    if content_found:
                        item_result.status = ComplianceStatus.CONFORME
                        item_result.observacao = "Funcionalidade encontrada"
                    else:
                        item_result.status = ComplianceStatus.ATENCAO
                        item_result.observacao = "Requer verificação manual"

                self.results.append(item_result)

        finally:
            await self._close_browser()

        return self._generate_report()

    def run_compliance_check_sync(self) -> Dict[str, Any]:
        """Versão síncrona do método run_compliance_check."""
        return asyncio.run(self.run_compliance_check())

    async def __aenter__(self):
        """Context manager entry."""
        await self._init_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self._close_browser()

    def _generate_report(self) -> Dict[str, Any]:
        """
        Gera o relatório de conformidade.
        """
        total = len(self.results)
        conformes = sum(1 for r in self.results if r.status == ComplianceStatus.CONFORME)
        atencao = sum(1 for r in self.results if r.status == ComplianceStatus.ATENCAO)
        irregulares = sum(1 for r in self.results if r.status == ComplianceStatus.IRREGULAR)

        percentual = (conformes / total) * 100 if total > 0 else 0

        return {
            "data_verificacao": datetime.now().isoformat(),
            "portal_url": self.BASE_URL,
            "resumo": {
                "total_itens": total,
                "conformes": conformes,
                "atencao": atencao,
                "irregulares": irregulares,
                "percentual_conformidade": round(percentual, 1),
                "score": f"{percentual:.0f}%"
            },
            "itens": [
                {
                    "id": r.id,
                    "item": r.nome,
                    "descricao": r.descricao,
                    "artigo": r.artigo,
                    "status": r.status.value,
                    "observacao": r.observacao,
                    "url": r.url_path,
                    "verificado_em": r.verificado_em
                }
                for r in self.results
            ],
            "recomendacoes": self._generate_recommendations()
        }

    def _generate_recommendations(self) -> List[str]:
        """
        Gera recomendações baseadas nos resultados.
        """
        recomendacoes = []

        for r in self.results:
            if r.status == ComplianceStatus.IRREGULAR:
                recomendacoes.append(
                    f"URGENTE: Regularizar '{r.nome}' - {r.artigo}"
                )
            elif r.status == ComplianceStatus.ATENCAO:
                recomendacoes.append(
                    f"ATENÇÃO: Verificar '{r.nome}' - {r.observacao}"
                )

        return recomendacoes

    def export_to_json(self, filepath: str) -> None:
        """
        Exporta os resultados para arquivo JSON.
        """
        import json

        report = self._generate_report()

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"Relatório exportado para {filepath}")

    def get_summary_for_dashboard(self) -> Dict[str, Any]:
        """
        Retorna resumo formatado para o dashboard.
        """
        report = self._generate_report()

        return {
            "laiScore": report["resumo"]["score"],
            "laiItems": report["resumo"]["total_itens"],
            "laiCompliant": report["resumo"]["conformes"],
            "lastCheck": report["data_verificacao"],
            "checklist": [
                {
                    "id": item["id"],
                    "item": item["item"],
                    "status": item["status"],
                    "note": item["observacao"] if item["status"] != "ok" else None,
                    "url": f"{self.BASE_URL}{item['url']}" if item["url"] else None
                }
                for item in report["itens"]
            ]
        }
