"""
Coletor de dados de pessoal/folha de pagamento do Portal de Transparência.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from .base import BaseCollector
import logging

logger = logging.getLogger(__name__)


class PessoalCollector(BaseCollector):
    """
    Coletor de dados de servidores e folha de pagamento.
    """

    ENDPOINT = "/api/servidores"

    def get_source_name(self) -> str:
        return "Servidores - Portal de Transparência de Marília"

    def collect(
        self,
        ano: Optional[int] = None,
        mes: Optional[int] = None,
        orgao: Optional[str] = None,
        cargo: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Coleta dados de servidores e remuneração.

        Args:
            ano: Ano de referência
            mes: Mês de referência
            orgao: Filtrar por órgão/secretaria
            cargo: Filtrar por cargo

        Returns:
            Lista de servidores com remuneração
        """
        if ano is None:
            ano = datetime.now().year
        if mes is None:
            mes = datetime.now().month

        url = f"{self.BASE_URL}{self.ENDPOINT}"
        params = {"ano": ano, "mes": mes}

        if orgao:
            params["orgao"] = orgao
        if cargo:
            params["cargo"] = cargo

        logger.info(f"Coletando dados de pessoal de {mes}/{ano}...")

        response = self._make_request(url, params=params)

        if response is None:
            logger.warning("API não disponível")
            return []

        try:
            data = response.json()
            return self._parse_response(data)
        except Exception as e:
            logger.error(f"Erro ao processar resposta: {e}")
            return []

    def _parse_response(self, data: Any) -> List[Dict[str, Any]]:
        """
        Processa a resposta da API.
        """
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("data", data.get("servidores", []))
        else:
            return []

        servidores = []
        for item in items:
            servidor = {
                "nome": item.get("nome", ""),
                "matricula": item.get("matricula", ""),
                "cpf_parcial": item.get("cpf", "")[:3] + ".***.***-**" if item.get("cpf") else "",
                "cargo": item.get("cargo", item.get("funcao", "")),
                "orgao": item.get("orgao", item.get("lotacao", "")),
                "vinculo": item.get("vinculo", item.get("tipo_vinculo", "")),
                "carga_horaria": item.get("carga_horaria", ""),
                "remuneracao_base": self._parse_valor(item.get("remuneracao_base", 0)),
                "outras_verbas": self._parse_valor(item.get("outras_verbas", 0)),
                "descontos": self._parse_valor(item.get("descontos", 0)),
                "remuneracao_liquida": self._parse_valor(item.get("remuneracao_liquida", 0)),
                "ano_referencia": item.get("ano", ""),
                "mes_referencia": item.get("mes", ""),
            }
            servidores.append(servidor)

        return servidores

    def _parse_valor(self, valor: Any) -> float:
        if isinstance(valor, (int, float)):
            return float(valor)
        if isinstance(valor, str):
            valor = valor.replace("R$", "").replace(".", "").replace(",", ".").strip()
            try:
                return float(valor)
            except ValueError:
                return 0.0
        return 0.0

    def collect_maiores_salarios(
        self,
        ano: int = None,
        mes: int = None,
        top_n: int = 20
    ) -> List[Dict]:
        """
        Retorna os maiores salários.
        """
        servidores = self.collect(ano=ano, mes=mes)

        ranking = sorted(
            servidores,
            key=lambda x: x.get("remuneracao_liquida", 0),
            reverse=True
        )

        return ranking[:top_n]

    def collect_por_orgao(self, ano: int = None, mes: int = None) -> Dict[str, Dict]:
        """
        Agrupa servidores por órgão.
        """
        servidores = self.collect(ano=ano, mes=mes)

        por_orgao = {}
        for s in servidores:
            orgao = s.get("orgao", "Não informado")
            if orgao not in por_orgao:
                por_orgao[orgao] = {"quantidade": 0, "folha_total": 0}

            por_orgao[orgao]["quantidade"] += 1
            por_orgao[orgao]["folha_total"] += s.get("remuneracao_liquida", 0)

        return dict(sorted(por_orgao.items(), key=lambda x: x[1]["folha_total"], reverse=True))

    def detect_acumulo_cargos(self) -> List[Dict]:
        """
        Detecta possível acúmulo ilegal de cargos.
        Verifica servidores com mesmo nome em diferentes vínculos.
        """
        servidores = self.collect()

        # Agrupar por nome
        por_nome = {}
        for s in servidores:
            nome = s.get("nome", "").upper().strip()
            if nome:
                por_nome.setdefault(nome, []).append(s)

        # Identificar múltiplos vínculos
        suspeitos = []
        for nome, registros in por_nome.items():
            if len(registros) > 1:
                total = sum(r.get("remuneracao_liquida", 0) for r in registros)
                suspeitos.append({
                    "nome": nome,
                    "quantidade_vinculos": len(registros),
                    "remuneracao_total": total,
                    "cargos": [r.get("cargo", "") for r in registros],
                    "orgaos": [r.get("orgao", "") for r in registros]
                })

        return sorted(suspeitos, key=lambda x: x["remuneracao_total"], reverse=True)
