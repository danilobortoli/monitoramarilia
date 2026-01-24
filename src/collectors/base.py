"""
Classe base para coletores de dados do Portal de Transparência de Marília.

O portal usa o sistema SMARAPD (PAI - Portal de Acesso à Informação),
que é baseado em JavaScript e requer renderização do navegador.
"""

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Tentar importar playwright, com fallback para requests
try:
    from playwright.async_api import async_playwright, Browser, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """
    Classe base abstrata para coletores de dados.

    O Portal de Transparência de Marília usa o sistema SMARAPD,
    que carrega dados via JavaScript. Esta classe usa Playwright
    para renderizar o conteúdo dinâmico.
    """

    # URL base do portal (SMARAPD PAI)
    BASE_URL = "https://transparencia.marilia.sp.gov.br"

    # Mapeamento de seções do portal SMARAPD
    SECTIONS = {
        "licitacoes": "/#/licitacao",
        "contratos": "/#/contrato",
        "despesas": "/#/despesa",
        "receitas": "/#/receita",
        "pessoal": "/#/pessoal",
        "diarias": "/#/diaria",
        "convenios": "/#/convenio",
    }

    def __init__(
        self,
        timeout: int = 60,
        max_retries: int = 3,
        headless: bool = True,
        cache_dir: Optional[Path] = None
    ):
        """
        Inicializa o coletor.

        Args:
            timeout: Tempo máximo de espera (segundos)
            max_retries: Número máximo de tentativas
            headless: Executar navegador sem interface gráfica
            cache_dir: Diretório para cache de dados
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.headless = headless
        self.cache_dir = cache_dir or Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Sessão HTTP para requisições simples
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "MonitoraMarilia/1.0 (MATRA - Controle Social)",
            "Accept": "application/json, text/html, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"
        })

        # Browser será inicializado quando necessário
        self._browser: Optional[Browser] = None
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
            logger.info("Navegador Playwright inicializado")

    async def _close_browser(self):
        """Fecha o navegador."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def _get_page_content(
        self,
        url: str,
        wait_selector: Optional[str] = None,
        wait_time: int = 5
    ) -> Optional[str]:
        """
        Obtém o conteúdo HTML de uma página após renderização JavaScript.

        Args:
            url: URL da página
            wait_selector: Seletor CSS para aguardar antes de extrair conteúdo
            wait_time: Tempo adicional de espera (segundos)

        Returns:
            HTML da página ou None em caso de falha
        """
        await self._init_browser()

        for attempt in range(self.max_retries):
            try:
                page = await self._browser.new_page()

                # Configurar timeout
                page.set_default_timeout(self.timeout * 1000)

                # Navegar para a página
                logger.info(f"Acessando: {url}")
                await page.goto(url, wait_until="networkidle")

                # Aguardar seletor específico se fornecido
                if wait_selector:
                    try:
                        await page.wait_for_selector(
                            wait_selector,
                            timeout=self.timeout * 1000
                        )
                    except Exception as e:
                        logger.warning(f"Seletor {wait_selector} não encontrado: {e}")

                # Tempo adicional para carregamento dinâmico
                await asyncio.sleep(wait_time)

                # Obter conteúdo HTML
                content = await page.content()
                await page.close()

                return content

            except Exception as e:
                logger.warning(f"Tentativa {attempt + 1}/{self.max_retries} falhou: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        logger.error(f"Falha ao acessar {url}")
        return None

    async def _extract_table_data(
        self,
        html: str,
        table_selector: str = "table"
    ) -> List[Dict[str, Any]]:
        """
        Extrai dados de uma tabela HTML.

        Args:
            html: Conteúdo HTML da página
            table_selector: Seletor CSS da tabela

        Returns:
            Lista de dicionários com os dados da tabela
        """
        soup = BeautifulSoup(html, "lxml")
        tables = soup.select(table_selector)

        if not tables:
            logger.warning(f"Nenhuma tabela encontrada com seletor: {table_selector}")
            return []

        all_data = []

        for table in tables:
            # Extrair cabeçalhos
            headers = []
            header_row = table.select_one("thead tr") or table.select_one("tr")
            if header_row:
                headers = [
                    th.get_text(strip=True)
                    for th in header_row.select("th, td")
                ]

            # Extrair linhas de dados
            rows = table.select("tbody tr") or table.select("tr")[1:]

            for row in rows:
                cells = row.select("td")
                if cells:
                    row_data = {}
                    for i, cell in enumerate(cells):
                        key = headers[i] if i < len(headers) else f"col_{i}"
                        # Normalizar chave
                        key = self._normalize_key(key)
                        row_data[key] = cell.get_text(strip=True)

                    if row_data:
                        all_data.append(row_data)

        return all_data

    def _normalize_key(self, key: str) -> str:
        """Normaliza uma chave de dicionário."""
        import re
        from unidecode import unidecode

        # Remover acentos e converter para minúsculas
        key = unidecode(key.lower())
        # Substituir espaços e caracteres especiais por underscore
        key = re.sub(r'[^a-z0-9]+', '_', key)
        # Remover underscores duplicados e nas extremidades
        key = re.sub(r'_+', '_', key).strip('_')

        return key or "campo"

    def _parse_currency(self, value: str) -> float:
        """Converte string de moeda brasileira para float."""
        if not value:
            return 0.0

        # Remover R$, pontos de milhar e converter vírgula decimal
        value = value.replace("R$", "").replace(".", "").replace(",", ".").strip()

        try:
            return float(value)
        except ValueError:
            return 0.0

    def _parse_date(self, value: str) -> Optional[str]:
        """Converte data brasileira para formato ISO."""
        if not value:
            return None

        # Tentar diferentes formatos
        formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]

        for fmt in formats:
            try:
                dt = datetime.strptime(value.strip(), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return value  # Retornar original se não conseguir converter

    def _save_cache(self, key: str, data: Any) -> None:
        """Salva dados em cache."""
        cache_file = self.cache_dir / f"{key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({
                "cached_at": datetime.now().isoformat(),
                "data": data
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"Cache salvo: {cache_file}")

    def _load_cache(self, key: str, max_age_hours: int = 24) -> Optional[Any]:
        """Carrega dados do cache se ainda válidos."""
        cache_file = self.cache_dir / f"{key}.json"

        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)

            cached_at = datetime.fromisoformat(cached["cached_at"])
            age_hours = (datetime.now() - cached_at).total_seconds() / 3600

            if age_hours <= max_age_hours:
                logger.info(f"Usando cache ({age_hours:.1f}h): {cache_file}")
                return cached["data"]

        except Exception as e:
            logger.warning(f"Erro ao ler cache: {e}")

        return None

    @abstractmethod
    async def collect(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Método abstrato para coleta de dados.
        Deve ser implementado por cada coletor específico.
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """Retorna o nome da fonte de dados."""
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """Retorna metadados sobre a coleta."""
        return {
            "source": self.get_source_name(),
            "base_url": self.BASE_URL,
            "collected_at": datetime.now().isoformat(),
            "collector_version": "2.0.0",
            "portal_type": "SMARAPD PAI"
        }

    def collect_sync(self, **kwargs) -> List[Dict[str, Any]]:
        """Versão síncrona do método collect."""
        return asyncio.run(self.collect(**kwargs))

    async def __aenter__(self):
        """Context manager entry."""
        await self._init_browser()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self._close_browser()
