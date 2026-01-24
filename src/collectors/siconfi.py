"""
Coletor de dados do SICONFI - Sistema de Informações Contábeis e Fiscais.

API do Tesouro Nacional com dados fiscais de todos os municípios brasileiros.
Fonte oficial e estruturada - muito mais confiável que scraping.

Documentação: http://apidatalake.tesouro.gov.br/docs/siconfi/
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class SiconfiCollector:
    """
    Coletor de dados fiscais via API SICONFI do Tesouro Nacional.

    Coleta:
    - RGF: Relatório de Gestão Fiscal (despesa com pessoal, dívida)
    - RREO: Relatório Resumido da Execução Orçamentária
    - DCA: Declaração de Contas Anuais (balanços)
    - Extratos: Status de entrega dos relatórios
    """

    BASE_URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
    CODIGO_IBGE_MARILIA = "3529005"

    def __init__(self, timeout: int = 30):
        """
        Inicializa o coletor SICONFI.

        Args:
            timeout: Tempo máximo de espera por requisição
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "MonitoraMarilia/2.0 (MATRA - Controle Social)"
        })

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """
        Faz requisição à API SICONFI.

        Args:
            endpoint: Endpoint da API (ex: /rgf, /rreo)
            params: Parâmetros da requisição

        Returns:
            Dados JSON ou None em caso de falha
        """
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            logger.info(f"SICONFI: {endpoint} - {params}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()

            # A API retorna {"items": [...]} quando há dados
            if isinstance(data, dict) and "items" in data:
                return data["items"]
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição SICONFI: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao processar resposta SICONFI: {e}")
            return None

    def get_rgf(
        self,
        ano: int,
        quadrimestre: int = 3,
        anexo: str = "RGF-Anexo 01",
        poder: str = "E"
    ) -> List[Dict[str, Any]]:
        """
        Busca Relatório de Gestão Fiscal (RGF).

        O RGF demonstra o cumprimento dos limites da LRF:
        - Despesa com pessoal (limite de 54% da RCL para Executivo)
        - Dívida consolidada
        - Operações de crédito
        - Garantias concedidas

        Args:
            ano: Ano do exercício
            quadrimestre: 1, 2 ou 3 (quadrimestre)
            anexo: Anexo do RGF (01 = Despesa com Pessoal)
            poder: E=Executivo, L=Legislativo

        Returns:
            Lista de dados do RGF
        """
        params = {
            "an_exercicio": ano,
            "nr_periodo": quadrimestre,
            "co_tipo_demonstrativo": "RGF",
            "no_anexo": anexo,
            "co_esfera": "M",  # Municipal
            "co_poder": poder,
            "id_ente": self.CODIGO_IBGE_MARILIA
        }

        data = self._make_request("rgf", params)
        return data if data else []

    def get_rreo(
        self,
        ano: int,
        bimestre: int = 6,
        anexo: str = "RREO-Anexo 01"
    ) -> List[Dict[str, Any]]:
        """
        Busca Relatório Resumido da Execução Orçamentária (RREO).

        O RREO apresenta:
        - Balanço orçamentário
        - Demonstrativo de receitas e despesas
        - Resultado primário e nominal
        - Restos a pagar

        Args:
            ano: Ano do exercício
            bimestre: 1 a 6 (bimestre)
            anexo: Anexo do RREO (01 = Balanço Orçamentário)

        Returns:
            Lista de dados do RREO
        """
        params = {
            "an_exercicio": ano,
            "nr_periodo": bimestre,
            "co_tipo_demonstrativo": "RREO",
            "no_anexo": anexo,
            "id_ente": self.CODIGO_IBGE_MARILIA
        }

        data = self._make_request("rreo", params)
        return data if data else []

    def get_dca(
        self,
        ano: int,
        anexo: str = "DCA-Anexo I-AB"
    ) -> List[Dict[str, Any]]:
        """
        Busca Declaração de Contas Anuais (DCA).

        A DCA contém os balanços anuais:
        - Balanço patrimonial
        - Demonstração das variações patrimoniais
        - Balanço orçamentário consolidado
        - Demonstrativo da dívida

        Args:
            ano: Ano do exercício
            anexo: Anexo da DCA

        Returns:
            Lista de dados da DCA
        """
        params = {
            "an_exercicio": ano,
            "no_anexo": anexo,
            "id_ente": self.CODIGO_IBGE_MARILIA
        }

        data = self._make_request("dca", params)
        return data if data else []

    def get_extrato_entregas(self, ano: int) -> List[Dict[str, Any]]:
        """
        Verifica status de entrega dos relatórios fiscais.

        Útil para verificar se o município está cumprindo
        os prazos de publicação obrigatória.

        Args:
            ano: Ano do exercício

        Returns:
            Lista com status das entregas
        """
        params = {
            "an_exercicio": ano,
            "id_ente": self.CODIGO_IBGE_MARILIA
        }

        data = self._make_request("extrato_entregas", params)
        return data if data else []

    def get_despesa_pessoal(self, ano: int) -> Dict[str, Any]:
        """
        Extrai indicadores de despesa com pessoal.

        Verifica se está dentro do limite de 54% da RCL (Executivo).

        Args:
            ano: Ano do exercício

        Returns:
            Dicionário com indicadores de pessoal
        """
        # Buscar RGF Anexo 01 (Despesa com Pessoal)
        rgf = self.get_rgf(ano, quadrimestre=3, anexo="RGF-Anexo 01")

        if not rgf:
            return {"erro": "Dados não disponíveis"}

        resultado = {
            "ano": ano,
            "fonte": "SICONFI/RGF",
            "indicadores": []
        }

        for item in rgf:
            if "DESPESA" in item.get("conta", "").upper() or "PESSOAL" in item.get("conta", "").upper():
                resultado["indicadores"].append({
                    "conta": item.get("conta", ""),
                    "coluna": item.get("coluna", ""),
                    "valor": item.get("valor", 0)
                })

        return resultado

    def get_receita_corrente_liquida(self, ano: int) -> Optional[float]:
        """
        Busca a Receita Corrente Líquida (RCL) do município.

        A RCL é a base de cálculo para os limites da LRF.

        Args:
            ano: Ano do exercício

        Returns:
            Valor da RCL ou None
        """
        # RCL está no RREO Anexo 03
        rreo = self.get_rreo(ano, bimestre=6, anexo="RREO-Anexo 03")

        if not rreo:
            return None

        for item in rreo:
            conta = item.get("conta", "").upper()
            if "RECEITA CORRENTE LÍQUIDA" in conta or "RCL" in conta:
                try:
                    return float(item.get("valor", 0))
                except (ValueError, TypeError):
                    pass

        return None

    def get_divida_consolidada(self, ano: int) -> Dict[str, Any]:
        """
        Busca dados da dívida consolidada.

        Args:
            ano: Ano do exercício

        Returns:
            Dicionário com dados da dívida
        """
        # Dívida está no RGF Anexo 02
        rgf = self.get_rgf(ano, quadrimestre=3, anexo="RGF-Anexo 02")

        if not rgf:
            return {"erro": "Dados não disponíveis"}

        resultado = {
            "ano": ano,
            "fonte": "SICONFI/RGF",
            "divida": []
        }

        for item in rgf:
            resultado["divida"].append({
                "conta": item.get("conta", ""),
                "coluna": item.get("coluna", ""),
                "valor": item.get("valor", 0)
            })

        return resultado

    def get_resumo_fiscal(self, ano: int) -> Dict[str, Any]:
        """
        Gera um resumo dos principais indicadores fiscais.

        Args:
            ano: Ano do exercício

        Returns:
            Dicionário com resumo fiscal
        """
        logger.info(f"Gerando resumo fiscal de Marília - {ano}")

        resumo = {
            "municipio": "Marília",
            "codigo_ibge": self.CODIGO_IBGE_MARILIA,
            "ano": ano,
            "data_consulta": datetime.now().isoformat(),
            "fonte": "SICONFI - Tesouro Nacional",
            "indicadores": {}
        }

        # Buscar RCL
        rcl = self.get_receita_corrente_liquida(ano)
        if rcl:
            resumo["indicadores"]["rcl"] = {
                "valor": rcl,
                "formatado": f"R$ {rcl/1_000_000:.1f} milhões"
            }

        # Buscar despesa com pessoal (último quadrimestre)
        pessoal = self.get_despesa_pessoal(ano)
        if pessoal.get("indicadores"):
            resumo["indicadores"]["despesa_pessoal"] = pessoal

        # Status das entregas
        entregas = self.get_extrato_entregas(ano)
        if entregas:
            resumo["status_entregas"] = len(entregas)
            resumo["entregas_detalhes"] = entregas[:5]  # Últimas 5

        return resumo

    def verificar_alertas_lrf(self, ano: int) -> List[Dict[str, Any]]:
        """
        Verifica possíveis alertas de descumprimento da LRF.

        Limites verificados:
        - Despesa com pessoal: 54% da RCL (Executivo)
        - Dívida consolidada: 120% da RCL
        - Operações de crédito: 16% da RCL

        Args:
            ano: Ano do exercício

        Returns:
            Lista de alertas identificados
        """
        alertas = []

        rcl = self.get_receita_corrente_liquida(ano)
        if not rcl or rcl <= 0:
            return [{"tipo": "warning", "mensagem": "RCL não disponível para cálculo"}]

        # Verificar despesa com pessoal
        rgf_pessoal = self.get_rgf(ano, quadrimestre=3, anexo="RGF-Anexo 01")

        for item in rgf_pessoal:
            conta = item.get("conta", "").upper()
            coluna = item.get("coluna", "").upper()

            # Buscar % da despesa total com pessoal
            if "DESPESA TOTAL COM PESSOAL" in conta and "%" in coluna:
                try:
                    percentual = float(item.get("valor", 0))

                    if percentual > 54:
                        alertas.append({
                            "tipo": "critico",
                            "categoria": "pessoal",
                            "titulo": "Limite de pessoal ultrapassado",
                            "descricao": f"Despesa com pessoal em {percentual:.1f}% da RCL (limite: 54%)",
                            "valor": percentual,
                            "limite": 54,
                            "data": datetime.now().strftime("%Y-%m-%d")
                        })
                    elif percentual > 51.3:  # Limite prudencial (95% do limite)
                        alertas.append({
                            "tipo": "alerta",
                            "categoria": "pessoal",
                            "titulo": "Limite prudencial de pessoal atingido",
                            "descricao": f"Despesa com pessoal em {percentual:.1f}% da RCL (limite prudencial: 51,3%)",
                            "valor": percentual,
                            "limite": 51.3,
                            "data": datetime.now().strftime("%Y-%m-%d")
                        })
                    elif percentual > 48.6:  # Limite de alerta (90% do limite)
                        alertas.append({
                            "tipo": "info",
                            "categoria": "pessoal",
                            "titulo": "Aproximando do limite de pessoal",
                            "descricao": f"Despesa com pessoal em {percentual:.1f}% da RCL (limite de alerta: 48,6%)",
                            "valor": percentual,
                            "limite": 48.6,
                            "data": datetime.now().strftime("%Y-%m-%d")
                        })
                except (ValueError, TypeError):
                    pass

        return alertas

    def get_dados_para_dashboard(self, ano: int = None) -> Dict[str, Any]:
        """
        Retorna dados formatados para o dashboard.

        Args:
            ano: Ano de referência (default: ano atual)

        Returns:
            Dicionário com dados para o dashboard
        """
        if ano is None:
            ano = datetime.now().year

        resumo = self.get_resumo_fiscal(ano)
        alertas = self.verificar_alertas_lrf(ano)

        return {
            "fonte": "SICONFI",
            "ano": ano,
            "ultima_atualizacao": datetime.now().isoformat(),
            "resumo": resumo,
            "alertas_lrf": alertas,
            "kpis": {
                "rcl": resumo.get("indicadores", {}).get("rcl", {}).get("formatado", "N/D"),
                "alertas_count": len(alertas),
                "alertas_criticos": len([a for a in alertas if a["tipo"] == "critico"])
            }
        }
