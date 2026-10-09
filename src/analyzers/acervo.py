"""
Histórico do Observatório: o que muda entre uma coleta e a seguinte.

O portal só mostra o estado atual. Para saber o que apareceu, mudou ou sumiu,
o Observatório guarda no repositório, em historico/:

    estado/{conjunto}.json        registros da última coleta (dados abertos)
    estado/diario-oficial.json    edições, só número, data e impressão digital do texto
    estado/despesas.json          IDs dos lançamentos de Despesas e Investimentos
    mudancas/AAAA-MM-DD.json      o que mudou em relação à coleta anterior
    radar.jsonl                   uma linha por coleta, com totais e resultados do radar
    cache/fornecedores_conhecidos.json

O git guarda as versões anteriores de cada arquivo de estado.
"""

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

# Conjuntos de dados abertos cujo conteúdo é comparado registro a registro.
CONJUNTOS_COMPARADOS = ("compra-direta", "contratos", "licitacoes", "obras")

# Campos que identificam o "mesmo" registro para reconhecer uma alteração. Não são
# únicos (há registros repetidos por completo), por isso a comparação usa a impressão
# digital do conteúdo e só recorre à identidade para parear o que saiu com o que entrou.
IDENTIDADE = {
    "compra-direta": ("modalidade", "numeroEdital", "numeroProcesso"),
    "licitacoes": ("modalidade", "numeroEdital", "numeroProcesso"),
    "contratos": ("tipo", "numeroContrato", "numeroProcesso"),
    "obras": ("titulo",),
}

# Mudam a cada sincronização do portal sem que o registro mude.
IGNORADOS = {"dataAtualizacao"}


def impressao(registro: Dict) -> str:
    """Impressão digital do conteúdo do registro."""
    conteudo = {k: v for k, v in registro.items() if k not in IGNORADOS}
    texto = json.dumps(conteudo, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(texto.encode("utf-8")).hexdigest()[:16]


def _identidade(conjunto: str, registro: Dict) -> tuple:
    return tuple(str(registro.get(c)) for c in IDENTIDADE[conjunto])


def comparar(conjunto: str, anteriores: List[Dict], atuais: List[Dict]) -> Dict:
    """
    Compara duas coletas de um conjunto.

    Returns:
        {"novos": [...], "alterados": [{"registro", "campos": {campo: [antes, depois]}}],
         "removidos": [...]}
    """
    saldo = Counter(impressao(r) for r in atuais)
    saldo.subtract(impressao(r) for r in anteriores)

    entraram, sairam = [], []
    restante = dict(saldo)
    for r in atuais:
        h = impressao(r)
        if restante.get(h, 0) > 0:
            entraram.append(r)
            restante[h] -= 1
    restante = {h: -n for h, n in saldo.items() if n < 0}
    for r in anteriores:
        h = impressao(r)
        if restante.get(h, 0) > 0:
            sairam.append(r)
            restante[h] -= 1

    # Um registro editado aparece como uma saída e uma entrada com a mesma identidade.
    por_id_entrada = defaultdict(list)
    por_id_saida = defaultdict(list)
    for r in entraram:
        por_id_entrada[_identidade(conjunto, r)].append(r)
    for r in sairam:
        por_id_saida[_identidade(conjunto, r)].append(r)

    novos, alterados, removidos = [], [], []
    for chave, lista in por_id_entrada.items():
        antigos = por_id_saida.get(chave, [])
        if len(lista) == 1 and len(antigos) == 1:
            antes, depois = antigos[0], lista[0]
            campos = {
                campo: [antes.get(campo), depois.get(campo)]
                for campo in sorted(set(antes) | set(depois))
                if campo not in IGNORADOS and antes.get(campo) != depois.get(campo)
            }
            alterados.append({"registro": depois, "campos": campos})
            por_id_saida.pop(chave)
        else:
            novos.extend(lista)
    for lista in por_id_saida.values():
        removidos.extend(lista)

    return {"novos": novos, "alterados": alterados, "removidos": removidos}


class Acervo:
    """Leitura e gravação do histórico em disco."""

    def __init__(self, raiz: str = "historico"):
        self.raiz = Path(raiz)

    def _ler(self, caminho: Path, padrao=None):
        if not caminho.exists():
            return padrao
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)

    def _gravar(self, caminho: Path, dados) -> None:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1, sort_keys=False)
            f.write("\n")

    # Estado da última coleta

    def ler_estado(self, nome: str, exercicio: int) -> Optional[List]:
        """Registros da coleta anterior, ou None se não houver (ou se for de outro exercício)."""
        estado = self._ler(self.raiz / "estado" / f"{nome}.json")
        if not estado or estado.get("exercicio") != exercicio:
            return None
        return estado["registros"]

    def gravar_estado(self, nome: str, exercicio: int, registros: List, ordenar=None) -> None:
        # Ordem estável, para que o git guarde só as linhas que mudaram.
        registros = sorted(registros, key=ordenar or impressao)
        self._gravar(self.raiz / "estado" / f"{nome}.json",
                     {"exercicio": exercicio, "registros": registros})

    # Mudanças e série

    def gravar_mudancas(self, dia: date, mudancas: Dict) -> None:
        self._gravar(self.raiz / "mudancas" / f"{dia.isoformat()}.json", mudancas)

    def registrar_coleta(self, linha: Dict) -> None:
        """Acrescenta uma linha a radar.jsonl, trocando a do mesmo dia se houver."""
        caminho = self.raiz / "radar.jsonl"
        linhas = []
        if caminho.exists():
            with open(caminho, encoding="utf-8") as f:
                linhas = [json.loads(l) for l in f if l.strip()]
        linhas = [l for l in linhas if l.get("data") != linha["data"]] + [linha]
        caminho.parent.mkdir(parents=True, exist_ok=True)
        with open(caminho, "w", encoding="utf-8") as f:
            for l in sorted(linhas, key=lambda l: l["data"]):
                f.write(json.dumps(l, ensure_ascii=False) + "\n")

    def serie(self) -> List[Dict]:
        caminho = self.raiz / "radar.jsonl"
        if not caminho.exists():
            return []
        with open(caminho, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]

    # Cache de fornecedores de anos anteriores

    def ler_fornecedores_conhecidos(self, anos: List[int], validade_dias: int = 30) -> Optional[List[str]]:
        """Chaves em cache, se forem dos mesmos anos e tiverem menos de `validade_dias`."""
        cache = self._ler(self.raiz / "cache" / "fornecedores_conhecidos.json")
        if not cache or cache.get("anos") != anos:
            return None
        gerado = datetime.fromisoformat(cache["gerado_em"])
        if (datetime.now() - gerado).days >= validade_dias:
            return None
        return cache["chaves"]

    def gravar_fornecedores_conhecidos(self, anos: List[int], chaves: Iterable[str]) -> None:
        self._gravar(self.raiz / "cache" / "fornecedores_conhecidos.json", {
            "gerado_em": datetime.now().isoformat(timespec="seconds"),
            "anos": anos,
            "chaves": sorted(chaves),
        })
