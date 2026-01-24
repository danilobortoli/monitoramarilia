"""
Analisador de Conformidade com a Lei de Acesso à Informação (LAI).
Verifica se o Portal de Transparência atende aos requisitos da Lei 12.527/2011.
"""

import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import logging

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
    url_esperada: Optional[str] = None
    status: ComplianceStatus = ComplianceStatus.NAO_VERIFICADO
    observacao: str = ""
    verificado_em: Optional[str] = None


class LAIComplianceAnalyzer:
    """
    Analisador de conformidade com a LAI (Lei 12.527/2011).
    Verifica os itens obrigatórios de transparência ativa (Art. 8º, §1º).
    """

    BASE_URL = "https://transparencia.marilia.sp.gov.br"

    # Checklist baseado no Art. 8º, §1º da Lei 12.527/2011
    CHECKLIST_LAI = [
        LAIItem(
            id=1,
            nome="Estrutura organizacional",
            descricao="Registro das competências e estrutura organizacional, endereços e telefones das respectivas unidades e horários de atendimento ao público",
            artigo="Art. 8º, §1º, I",
            url_esperada="/estrutura"
        ),
        LAIItem(
            id=2,
            nome="Competências e atribuições",
            descricao="Competências e atribuições dos órgãos e entidades",
            artigo="Art. 8º, §1º, I",
            url_esperada="/competencias"
        ),
        LAIItem(
            id=3,
            nome="Endereços e telefones",
            descricao="Endereços e telefones das unidades",
            artigo="Art. 8º, §1º, I",
            url_esperada="/contato"
        ),
        LAIItem(
            id=4,
            nome="Horários de atendimento",
            descricao="Horários de atendimento ao público",
            artigo="Art. 8º, §1º, I",
            url_esperada="/atendimento"
        ),
        LAIItem(
            id=5,
            nome="Repasses e transferências",
            descricao="Registros de quaisquer repasses ou transferências de recursos financeiros",
            artigo="Art. 8º, §1º, II",
            url_esperada="/repasses"
        ),
        LAIItem(
            id=6,
            nome="Despesas",
            descricao="Registros das despesas (execução orçamentária e financeira detalhada)",
            artigo="Art. 8º, §1º, III",
            url_esperada="/despesas"
        ),
        LAIItem(
            id=7,
            nome="Licitações e contratos",
            descricao="Informações concernentes a procedimentos licitatórios, inclusive os respectivos editais e resultados, bem como a todos os contratos celebrados",
            artigo="Art. 8º, §1º, IV",
            url_esperada="/licitacoes"
        ),
        LAIItem(
            id=8,
            nome="Receitas",
            descricao="Dados gerais para o acompanhamento de programas, ações, projetos e obras",
            artigo="Art. 8º, §1º, V",
            url_esperada="/receitas"
        ),
        LAIItem(
            id=9,
            nome="Perguntas frequentes",
            descricao="Respostas a perguntas mais frequentes da sociedade",
            artigo="Art. 8º, §1º, VI",
            url_esperada="/faq"
        ),
        LAIItem(
            id=10,
            nome="Ferramenta de pesquisa",
            descricao="Ferramenta de pesquisa de conteúdo que permita o acesso à informação",
            artigo="Art. 8º, §3º, I",
            url_esperada="/pesquisa"
        ),
        LAIItem(
            id=11,
            nome="Dados em formatos abertos",
            descricao="Possibilidade de gravação de relatórios em diversos formatos eletrônicos, inclusive abertos e não proprietários",
            artigo="Art. 8º, §3º, II",
            url_esperada=None
        ),
        LAIItem(
            id=12,
            nome="Relatório estatístico LAI",
            descricao="Relatório estatístico contendo a quantidade de pedidos de informação recebidos, atendidos e indeferidos",
            artigo="Art. 30, III",
            url_esperada="/relatorio-lai"
        ),
    ]

    def __init__(self, timeout: int = 15):
        """
        Inicializa o analisador.

        Args:
            timeout: Tempo máximo de espera por requisição
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "MonitoraMarilia/1.0 (Verificacao LAI - MATRA)"
        })
        self.results: List[LAIItem] = []

    def check_url_accessible(self, url: str) -> bool:
        """
        Verifica se uma URL está acessível.
        """
        try:
            response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            return response.status_code == 200
        except requests.RequestException:
            try:
                response = self.session.get(url, timeout=self.timeout)
                return response.status_code == 200
            except requests.RequestException:
                return False

    def check_content_exists(self, url: str, keywords: List[str]) -> bool:
        """
        Verifica se uma página contém determinadas palavras-chave.
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code != 200:
                return False

            content = response.text.lower()
            return any(kw.lower() in content for kw in keywords)
        except requests.RequestException:
            return False

    def run_compliance_check(self) -> Dict[str, Any]:
        """
        Executa a verificação completa de conformidade LAI.

        Returns:
            Dicionário com resultados da verificação
        """
        logger.info("Iniciando verificação de conformidade LAI...")

        self.results = []
        agora = datetime.now().isoformat()

        for item in self.CHECKLIST_LAI:
            logger.info(f"Verificando: {item.nome}")

            item_result = LAIItem(
                id=item.id,
                nome=item.nome,
                descricao=item.descricao,
                artigo=item.artigo,
                url_esperada=item.url_esperada,
                verificado_em=agora
            )

            if item.url_esperada:
                full_url = f"{self.BASE_URL}/#/{item.url_esperada.lstrip('/')}"

                if self.check_url_accessible(full_url):
                    item_result.status = ComplianceStatus.CONFORME
                    item_result.observacao = "URL acessível"
                else:
                    # Tentar URL alternativa sem hash
                    alt_url = f"{self.BASE_URL}{item.url_esperada}"
                    if self.check_url_accessible(alt_url):
                        item_result.status = ComplianceStatus.CONFORME
                        item_result.observacao = "URL acessível (alternativa)"
                    else:
                        item_result.status = ComplianceStatus.ATENCAO
                        item_result.observacao = "URL não acessível ou requer verificação manual"
            else:
                # Itens que requerem verificação manual
                item_result.status = ComplianceStatus.ATENCAO
                item_result.observacao = "Requer verificação manual"

            self.results.append(item_result)

        return self._generate_report()

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
                    "url": r.url_esperada,
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
                    "url": f"{self.BASE_URL}/#/{item['url'].lstrip('/')}" if item["url"] else None
                }
                for item in report["itens"]
            ]
        }
