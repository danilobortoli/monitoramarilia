"""
Leitura do acompanhamento da MATRA no Notion (somente leitura).

A rotina "DOMM na nuvem" grava as edições do Diário Oficial, os achados e os
casos no Notion. O Observatório só lê essas bases para mostrar, no site e no
boletim, números agregados: situação das edições, achados em aberto e os casos
que estiverem marcados para publicação. Nada é gravado no Notion.

Requer uma integração interna do Notion com acesso às bases (variável de
ambiente NOTION_TOKEN). Sem a chave, o coletor fica inativo e o site segue
sem esses dados.

API: https://developers.notion.com/reference/post-database-query
"""

import logging
import os
from typing import Dict, Iterable, List, Optional

import requests

logger = logging.getLogger(__name__)

# Achados que ainda pedem providência ou acompanhamento.
STATUS_EM_ABERTO = ("aberta", "oficiada", "respondida", "representada")

# Checkbox na base Casos que libera o caso para aparecer no site.
PROPRIEDADE_PUBLICO = "No Observatório"


def _texto(prop: Optional[Dict]) -> str:
    if not prop:
        return ""
    partes = prop.get(prop.get("type"), [])
    if isinstance(partes, list):
        return "".join(p.get("plain_text", "") for p in partes).strip()
    return ""


def _valor(prop: Optional[Dict]):
    """Valor simples de uma propriedade do Notion (título, texto, número, seleção, data, checkbox)."""
    if not prop:
        return None
    tipo = prop.get("type")
    if tipo in ("title", "rich_text"):
        return _texto(prop)
    if tipo == "number":
        return prop.get("number")
    if tipo == "select":
        return (prop.get("select") or {}).get("name")
    if tipo == "date":
        return (prop.get("date") or {}).get("start")
    if tipo == "checkbox":
        return prop.get("checkbox")
    return None


class NotionMatraCollector:
    """Consulta as bases Edições DOMM, Achados DOMM e Casos."""

    API_URL = "https://api.notion.com/v1"
    VERSAO = "2022-06-28"

    def __init__(self, bases: Dict[str, str], token: Optional[str] = None,
                 timeout: int = 60, session: Optional[requests.Session] = None):
        """
        Args:
            bases: IDs das bases {"edicoes": ..., "achados": ..., "casos": ...}
            token: Chave da integração (ou NOTION_TOKEN no ambiente)
        """
        self.bases = bases
        self.token = token if token is not None else os.environ.get("NOTION_TOKEN", "")
        self.timeout = timeout
        self.session = session or requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": self.VERSAO,
            "Content-Type": "application/json",
        })

    @property
    def ativo(self) -> bool:
        return bool(self.token)

    def _consultar(self, base: str, filtro: Optional[Dict] = None,
                   ordem: Optional[List[Dict]] = None, limite: Optional[int] = None) -> List[Dict]:
        """Páginas de uma base, seguindo a paginação até `limite`."""
        paginas, cursor = [], None
        while True:
            corpo = {"page_size": 100}
            if filtro:
                corpo["filter"] = filtro
            if ordem:
                corpo["sorts"] = ordem
            if cursor:
                corpo["start_cursor"] = cursor
            resposta = self.session.post(f"{self.API_URL}/databases/{self.bases[base]}/query",
                                         json=corpo, timeout=self.timeout)
            resposta.raise_for_status()
            dados = resposta.json()
            paginas.extend(dados.get("results", []))
            if limite and len(paginas) >= limite:
                return paginas[:limite]
            if not dados.get("has_more"):
                return paginas
            cursor = dados.get("next_cursor")

    def _propriedades_da_base(self, base: str) -> Dict:
        resposta = self.session.get(f"{self.API_URL}/databases/{self.bases[base]}", timeout=self.timeout)
        resposta.raise_for_status()
        return resposta.json().get("properties", {})

    def edicoes_recentes(self, quantidade: int = 10) -> List[Dict]:
        """Últimas edições registradas na base Edições DOMM."""
        paginas = self._consultar("edicoes", ordem=[{"property": "Número", "direction": "descending"}],
                                  limite=quantidade)
        edicoes = []
        for p in paginas:
            props = p.get("properties", {})
            numero = _valor(props.get("Número"))
            edicoes.append({
                "numero": int(numero) if numero is not None else None,
                "data": _valor(props.get("Data")),
                "situacao": _valor(props.get("Situação")),
                "origem": _valor(props.get("Origem")),
                "atos": _valor(props.get("Atos")),
                "paginas": _valor(props.get("Páginas")),
                "irregularidades": _valor(props.get("Irregularidades")),
            })
        return edicoes

    def achados(self, desde: Optional[str] = None) -> List[Dict]:
        """
        Achados da base Achados DOMM, só com os campos usados em contagens.

        Args:
            desde: Data (AAAA-MM-DD) mínima da edição; sem ela, todos os achados
        """
        filtro = {"property": "Data DOMM", "date": {"on_or_after": desde}} if desde else None
        achados = []
        for p in self._consultar("achados", filtro=filtro):
            props = p.get("properties", {})
            edicao = _valor(props.get("Edição"))
            achados.append({
                "edicao": int(edicao) if edicao is not None else None,
                "data": _valor(props.get("Data DOMM")),
                "tipo": _valor(props.get("Tipo")),
                "gravidade": _valor(props.get("Gravidade")),
                "status": _valor(props.get("Status")),
                "acao": _valor(props.get("Ação")),
            })
        return achados

    def casos_publicos(self) -> Optional[List[Dict]]:
        """
        Casos ativos da MATRA marcados para aparecer no site.

        Returns:
            Lista de {"caso", "fase"}; None se a base não tiver a caixa PROPRIEDADE_PUBLICO
            (nesse caso, nenhum caso do Notion é publicado).
        """
        if PROPRIEDADE_PUBLICO not in self._propriedades_da_base("casos"):
            logger.info("Base Casos sem a propriedade '%s': casos do Notion não são publicados.",
                        PROPRIEDADE_PUBLICO)
            return None
        filtro = {"and": [
            {"property": "Frente", "select": {"equals": "MATRA"}},
            {"property": "Status", "select": {"equals": "Ativo"}},
            {"property": PROPRIEDADE_PUBLICO, "checkbox": {"equals": True}},
        ]}
        casos = []
        for p in self._consultar("casos", filtro=filtro):
            props = p.get("properties", {})
            casos.append({"caso": _valor(props.get("Caso")), "fase": _valor(props.get("Fase"))})
        return casos

    def resumo(self, inicio_semana: Optional[str] = None) -> Dict:
        """Tudo o que o Observatório usa do Notion, já agregado."""
        edicoes = self.edicoes_recentes()
        achados = self.achados()
        return {
            "edicoes": edicoes,
            "achados": resumir_achados(achados, [e["numero"] for e in edicoes[:2] if e["numero"]],
                                       inicio_semana),
            "casos": self.casos_publicos(),
        }


def resumir_achados(achados: Iterable[Dict], ultimas_edicoes: List[int],
                    inicio_semana: Optional[str] = None) -> Dict:
    """Contagens de achados: em aberto, das duas últimas edições e da semana."""
    achados = list(achados)
    abertos = [a for a in achados if a["status"] in STATUS_EM_ABERTO]

    def contar(lista, campo):
        contagem = {}
        for a in lista:
            chave = a.get(campo) or "não informado"
            contagem[chave] = contagem.get(chave, 0) + 1
        return contagem

    recentes = [a for a in abertos if a["edicao"] in ultimas_edicoes]
    semana = [a for a in achados if inicio_semana and (a["data"] or "") >= inicio_semana]
    return {
        "total": len(achados),
        "em_aberto": len(abertos),
        "em_aberto_por_status": contar(abertos, "status"),
        "em_aberto_por_gravidade": contar(abertos, "gravidade"),
        "em_aberto_por_tipo": contar(abertos, "tipo"),
        "ultimas_edicoes": ultimas_edicoes,
        "em_aberto_ultimas_edicoes": len(recentes),
        "graves_ultimas_edicoes": sum(1 for a in recentes if a["gravidade"] == "grave"),
        "semana": {
            "inicio": inicio_semana,
            "novos": len(semana),
            "por_gravidade": contar(semana, "gravidade"),
            "por_acao": contar(semana, "acao"),
        },
    }
