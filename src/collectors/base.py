"""
Classe base para coletores de dados do Portal de Transparência.
"""

import requests
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """
    Classe base abstrata para coletores de dados.
    Todos os coletores específicos devem herdar desta classe.
    """

    BASE_URL = "https://transparencia.marilia.sp.gov.br"

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """
        Inicializa o coletor.

        Args:
            timeout: Tempo máximo de espera por requisição (segundos)
            max_retries: Número máximo de tentativas em caso de falha
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "MonitoraMarilia/1.0 (Controle Social - MATRA)",
            "Accept": "application/json, text/html",
            "Accept-Language": "pt-BR,pt;q=0.9"
        })

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Optional[requests.Response]:
        """
        Faz uma requisição HTTP com tratamento de erros e retentativas.

        Args:
            url: URL da requisição
            method: Método HTTP (GET, POST, etc.)
            params: Parâmetros de query string
            data: Dados para POST

        Returns:
            Response object ou None em caso de falha
        """
        for attempt in range(self.max_retries):
            try:
                if method.upper() == "GET":
                    response = self.session.get(
                        url,
                        params=params,
                        timeout=self.timeout
                    )
                elif method.upper() == "POST":
                    response = self.session.post(
                        url,
                        params=params,
                        data=data,
                        timeout=self.timeout
                    )
                else:
                    raise ValueError(f"Método HTTP não suportado: {method}")

                response.raise_for_status()
                return response

            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"Tentativa {attempt + 1}/{self.max_retries} falhou: {e}"
                )
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Backoff exponencial

        logger.error(f"Falha ao acessar {url} após {self.max_retries} tentativas")
        return None

    @abstractmethod
    def collect(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Método abstrato para coleta de dados.
        Deve ser implementado por cada coletor específico.

        Returns:
            Lista de dicionários com os dados coletados
        """
        pass

    @abstractmethod
    def get_source_name(self) -> str:
        """
        Retorna o nome da fonte de dados.
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """
        Retorna metadados sobre a coleta.
        """
        return {
            "source": self.get_source_name(),
            "base_url": self.BASE_URL,
            "collected_at": datetime.now().isoformat(),
            "collector_version": "1.0.0"
        }
