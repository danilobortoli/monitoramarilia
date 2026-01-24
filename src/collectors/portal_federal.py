"""
Coletor de dados do Portal da Transparência do Governo Federal.

API REST com dados de convênios, transferências, CEIS, CNEP, emendas parlamentares.
Requer chave de API (cadastro em: https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email)

Documentação: https://api.portaldatransparencia.gov.br/swagger-ui.html
"""

import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class PortalFederalCollector:
    """
    Coletor de dados do Portal da Transparência do Governo Federal.

    Coleta:
    - Convênios federais com o município
    - Transferências voluntárias e constitucionais
    - Emendas parlamentares destinadas ao município
    - CEIS: Cadastro de Empresas Inidôneas e Suspensas
    - CNEP: Cadastro Nacional de Empresas Punidas
    - CEPIM: Cadastro de Entidades Privadas Sem Fins Lucrativos Impedidas
    """

    BASE_URL = "https://api.portaldatransparencia.gov.br/api-de-dados"
    CODIGO_IBGE_MARILIA = "3529005"
    CODIGO_SIAFI_MARILIA = "6697"  # Código SIAFI do município

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        """
        Inicializa o coletor.

        Args:
            api_key: Chave de API (ou via variável de ambiente PORTAL_TRANSPARENCIA_KEY)
            timeout: Tempo máximo de espera por requisição
        """
        self.api_key = api_key or os.environ.get("PORTAL_TRANSPARENCIA_KEY", "")
        self.timeout = timeout
        self.session = requests.Session()

        if self.api_key:
            self.session.headers.update({
                "chave-api-dados": self.api_key,
                "Accept": "application/json"
            })
        else:
            logger.warning(
                "API Key não configurada. Cadastre em: "
                "https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email"
            )

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[List[Dict]]:
        """
        Faz requisição à API do Portal da Transparência.

        Args:
            endpoint: Endpoint da API
            params: Parâmetros da requisição

        Returns:
            Lista de dados ou None em caso de falha
        """
        if not self.api_key:
            logger.error("API Key necessária para acessar o Portal da Transparência")
            return None

        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}

        try:
            logger.info(f"Portal Federal: {endpoint}")
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()

            data = response.json()
            return data if isinstance(data, list) else [data] if data else []

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                logger.error("API Key inválida ou expirada")
            elif e.response.status_code == 429:
                logger.error("Limite de requisições excedido")
            else:
                logger.error(f"Erro HTTP: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro na requisição: {e}")
            return None

    def get_convenios(
        self,
        ano: Optional[int] = None,
        pagina: int = 1,
        quantidade: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Busca convênios federais com o município de Marília.

        Convênios são acordos entre o governo federal e estados/municípios
        para repasse de recursos com contrapartida.

        Args:
            ano: Ano de referência (opcional)
            pagina: Página de resultados
            quantidade: Itens por página (máx 500)

        Returns:
            Lista de convênios
        """
        params = {
            "codigoIBGE": self.CODIGO_IBGE_MARILIA,
            "pagina": pagina,
            "quantidade": min(quantidade, 500)
        }

        if ano:
            params["ano"] = ano

        data = self._make_request("convenios", params)

        if not data:
            return []

        # Normalizar dados
        convenios = []
        for item in data:
            convenios.append({
                "numero": item.get("numero", ""),
                "objeto": item.get("objeto", ""),
                "valor_global": item.get("valorGlobal", 0),
                "valor_repasse": item.get("valorRepasse", 0),
                "valor_contrapartida": item.get("valorContrapartida", 0),
                "valor_liberado": item.get("valorLiberado", 0),
                "data_inicio": item.get("dataInicioVigencia", ""),
                "data_fim": item.get("dataFimVigencia", ""),
                "situacao": item.get("situacao", ""),
                "orgao_superior": item.get("orgaoSuperior", {}).get("nome", ""),
                "orgao_concedente": item.get("orgao", {}).get("nome", ""),
                "proponente": item.get("proponente", {}).get("nome", ""),
                "fonte": "Portal Transparência Federal"
            })

        return convenios

    def get_transferencias(
        self,
        ano: int,
        mes: Optional[int] = None,
        pagina: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Busca transferências de recursos federais para Marília.

        Inclui transferências constitucionais, legais e voluntárias.

        Args:
            ano: Ano de referência
            mes: Mês (opcional, 1-12)
            pagina: Página de resultados

        Returns:
            Lista de transferências
        """
        params = {
            "codigoIBGE": self.CODIGO_IBGE_MARILIA,
            "ano": ano,
            "pagina": pagina
        }

        if mes:
            params["mes"] = mes

        data = self._make_request("transferencias", params)

        if not data:
            return []

        transferencias = []
        for item in data:
            transferencias.append({
                "tipo": item.get("tipo", ""),
                "acao": item.get("acao", {}).get("nome", ""),
                "programa": item.get("programa", {}).get("nome", ""),
                "valor": item.get("valor", 0),
                "data": item.get("dataTransferencia", ""),
                "orgao": item.get("orgao", {}).get("nome", ""),
                "fonte": "Portal Transparência Federal"
            })

        return transferencias

    def get_emendas_parlamentares(
        self,
        ano: int,
        pagina: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Busca emendas parlamentares destinadas a Marília.

        Emendas são recursos direcionados por parlamentares
        para projetos específicos no município.

        Args:
            ano: Ano de referência
            pagina: Página de resultados

        Returns:
            Lista de emendas
        """
        params = {
            "codigoIBGE": self.CODIGO_IBGE_MARILIA,
            "ano": ano,
            "pagina": pagina
        }

        data = self._make_request("emendas-parlamentares", params)

        if not data:
            return []

        emendas = []
        for item in data:
            emendas.append({
                "numero": item.get("numero", ""),
                "autor": item.get("nomeAutor", ""),
                "localidade": item.get("localidade", ""),
                "funcao": item.get("funcao", {}).get("nome", ""),
                "subfuncao": item.get("subfuncao", {}).get("nome", ""),
                "valor_empenhado": item.get("valorEmpenhado", 0),
                "valor_liquidado": item.get("valorLiquidado", 0),
                "valor_pago": item.get("valorPago", 0),
                "ano": ano,
                "fonte": "Portal Transparência Federal"
            })

        return emendas

    def verificar_empresa_ceis(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """
        Verifica se uma empresa está no CEIS (Cadastro de Empresas Inidôneas e Suspensas).

        Empresas no CEIS estão impedidas de contratar com a administração pública.

        Args:
            cnpj: CNPJ da empresa (apenas números)

        Returns:
            Dados da sanção ou None se não encontrado
        """
        cnpj_limpo = "".join(filter(str.isdigit, cnpj))

        params = {"cnpjSancionado": cnpj_limpo}
        data = self._make_request("ceis", params)

        if data:
            return {
                "situacao": "SANCIONADA",
                "cadastro": "CEIS",
                "detalhes": data[0] if data else {},
                "fonte": "Portal Transparência Federal"
            }

        return None

    def verificar_empresa_cnep(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """
        Verifica se uma empresa está no CNEP (Cadastro Nacional de Empresas Punidas).

        O CNEP lista empresas punidas com base na Lei Anticorrupção.

        Args:
            cnpj: CNPJ da empresa (apenas números)

        Returns:
            Dados da punição ou None se não encontrado
        """
        cnpj_limpo = "".join(filter(str.isdigit, cnpj))

        params = {"cnpjSancionado": cnpj_limpo}
        data = self._make_request("cnep", params)

        if data:
            return {
                "situacao": "PUNIDA",
                "cadastro": "CNEP",
                "detalhes": data[0] if data else {},
                "fonte": "Portal Transparência Federal"
            }

        return None

    def verificar_empresa_cepim(self, cnpj: str) -> Optional[Dict[str, Any]]:
        """
        Verifica se uma entidade está no CEPIM (Entidades Privadas Sem Fins Lucrativos Impedidas).

        Args:
            cnpj: CNPJ da entidade (apenas números)

        Returns:
            Dados do impedimento ou None se não encontrado
        """
        cnpj_limpo = "".join(filter(str.isdigit, cnpj))

        params = {"cnpjSancionado": cnpj_limpo}
        data = self._make_request("cepim", params)

        if data:
            return {
                "situacao": "IMPEDIDA",
                "cadastro": "CEPIM",
                "detalhes": data[0] if data else {},
                "fonte": "Portal Transparência Federal"
            }

        return None

    def verificar_fornecedor_completo(self, cnpj: str) -> Dict[str, Any]:
        """
        Verifica um fornecedor em todos os cadastros de sanções.

        Args:
            cnpj: CNPJ do fornecedor

        Returns:
            Resultado consolidado de todas as verificações
        """
        resultado = {
            "cnpj": cnpj,
            "verificado_em": datetime.now().isoformat(),
            "situacao": "REGULAR",
            "sancoes": []
        }

        # Verificar CEIS
        ceis = self.verificar_empresa_ceis(cnpj)
        if ceis:
            resultado["situacao"] = "IRREGULAR"
            resultado["sancoes"].append(ceis)

        # Verificar CNEP
        cnep = self.verificar_empresa_cnep(cnpj)
        if cnep:
            resultado["situacao"] = "IRREGULAR"
            resultado["sancoes"].append(cnep)

        # Verificar CEPIM
        cepim = self.verificar_empresa_cepim(cnpj)
        if cepim:
            resultado["situacao"] = "IRREGULAR"
            resultado["sancoes"].append(cepim)

        return resultado

    def get_totais_transferencias(self, ano: int) -> Dict[str, float]:
        """
        Calcula totais de transferências federais por tipo.

        Args:
            ano: Ano de referência

        Returns:
            Dicionário com totais por tipo de transferência
        """
        transferencias = []

        # Buscar todas as páginas
        pagina = 1
        while True:
            dados = self.get_transferencias(ano, pagina=pagina)
            if not dados:
                break
            transferencias.extend(dados)
            if len(dados) < 100:  # Última página
                break
            pagina += 1

        # Agrupar por tipo
        totais = {}
        for t in transferencias:
            tipo = t.get("tipo", "Outros")
            totais[tipo] = totais.get(tipo, 0) + t.get("valor", 0)

        return totais

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

        if not self.api_key:
            return {
                "erro": "API Key não configurada",
                "instrucoes": "Cadastre em: https://portaldatransparencia.gov.br/api-de-dados/cadastrar-email"
            }

        logger.info(f"Gerando dados Portal Federal para dashboard - {ano}")

        # Convênios
        convenios = self.get_convenios(ano)
        total_convenios = sum(c.get("valor_repasse", 0) for c in convenios)

        # Emendas
        emendas = self.get_emendas_parlamentares(ano)
        total_emendas = sum(e.get("valor_pago", 0) for e in emendas)

        # Transferências
        totais_transf = self.get_totais_transferencias(ano)
        total_transferencias = sum(totais_transf.values())

        return {
            "fonte": "Portal Transparência Federal",
            "ano": ano,
            "ultima_atualizacao": datetime.now().isoformat(),
            "convenios": {
                "quantidade": len(convenios),
                "valor_total": total_convenios,
                "valor_fmt": f"R$ {total_convenios/1_000_000:.2f}M",
                "lista": convenios[:5]  # Top 5
            },
            "emendas": {
                "quantidade": len(emendas),
                "valor_total": total_emendas,
                "valor_fmt": f"R$ {total_emendas/1_000_000:.2f}M",
                "por_autor": self._agrupar_emendas_por_autor(emendas)[:5]
            },
            "transferencias": {
                "valor_total": total_transferencias,
                "valor_fmt": f"R$ {total_transferencias/1_000_000:.2f}M",
                "por_tipo": totais_transf
            }
        }

    def _agrupar_emendas_por_autor(self, emendas: List[Dict]) -> List[Dict]:
        """Agrupa emendas por autor."""
        totais = {}
        for e in emendas:
            autor = e.get("autor", "Não informado")
            if autor not in totais:
                totais[autor] = {"autor": autor, "valor": 0, "quantidade": 0}
            totais[autor]["valor"] += e.get("valor_pago", 0)
            totais[autor]["quantidade"] += 1

        return sorted(totais.values(), key=lambda x: x["valor"], reverse=True)
