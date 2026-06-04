"""
Diagnóstico TEMPORÁRIO de schema das APIs (SICONFI e TCE-SP).

Imprime no log do job os nomes reais dos campos retornados, para corrigir
o mapeamento dos coletores. Resiliente a throttling: SICONFI primeiro e
TCE-SP com timeout curto. Pode ser removido após o ajuste.
"""
import datetime
import json
import os

import requests

S = requests.Session()
S.headers.update({"Accept": "application/json", "User-Agent": "MonitoraMarilia/diag"})
ano = datetime.date.today().year
OUT = {}  # capturado e gravado em docs/data/_diag_schema.json para leitura via git


def siconfi(endpoint, params, titulo, filtro):
    try:
        r = S.get(
            f"https://apidatalake.tesouro.gov.br/ords/siconfi/tt/{endpoint}",
            params=params, timeout=45,
        )
        print(f"\n===== {titulo} -> HTTP {r.status_code} =====", flush=True)
        if r.ok:
            items = r.json().get("items", [])
            print(f"  total: {len(items)}")
            achados = []
            if items:
                print(f"  chaves: {list(items[0].keys())}")
                OUT[titulo] = {"chaves": list(items[0].keys()),
                               "colunas": sorted(set(i.get('coluna', '') for i in items))}
            for it in items:
                conta = (it.get("conta") or "").upper()
                if any(f in conta for f in filtro):
                    linha = {k: it.get(k) for k in ("cod_conta", "conta", "coluna", "valor")}
                    achados.append(linha)
                    print("   >>>", json.dumps(linha, ensure_ascii=False))
            OUT.setdefault(titulo, {})["achados"] = achados[:40]
    except Exception as e:
        print(f"{titulo} erro:", e, flush=True)
        OUT[titulo] = {"erro": str(e)}


# 1) SICONFI RREO Anexo 03 (RCL) — período fechado do ano anterior
siconfi("rreo",
        {"an_exercicio": ano - 1, "nr_periodo": 6, "co_tipo_demonstrativo": "RREO",
         "no_anexo": "RREO-Anexo 03", "id_ente": "3529005"},
        f"RREO Anexo03 {ano-1}/bim6 (RCL)",
        ("CORRENTE LÍQUIDA", "CORRENTE LIQUIDA", "RCL"))

# 2) SICONFI RGF Anexo 01 (Despesa com pessoal)
siconfi("rgf",
        {"an_exercicio": ano - 1, "nr_periodo": 3, "co_tipo_demonstrativo": "RGF",
         "no_anexo": "RGF-Anexo 01", "co_esfera": "M", "co_poder": "E", "id_ente": "3529005"},
        f"RGF Anexo01 {ano-1}/quad3 (Pessoal)",
        ("DESPESA TOTAL COM PESSOAL", "PESSOAL", "RECEITA CORRENTE LÍQUIDA"))

# 3) TCE-SP — despesas brutas (nomes de valor/fornecedor/evento). Timeout curto.
print("\n===== TCE-SP despesas (schema bruto) =====", flush=True)
for tano, tmes in ((ano, 2), (ano, 1), (ano - 1, 12)):
    try:
        r = S.get(
            f"https://transparencia.tce.sp.gov.br/api/json/despesas/marilia/{tano}/{tmes}",
            timeout=15,
        )
        print(f"  TCE {tano}/{tmes} -> HTTP {r.status_code}", flush=True)
        if r.ok:
            data = r.json()
            data = data if isinstance(data, list) else [data]
            if data:
                print(f"  total: {len(data)}")
                print(f"  chaves: {list(data[0].keys())}")
                for it in data[:3]:
                    print("  amostra:", json.dumps(it, ensure_ascii=False)[:700])
                OUT["TCE despesas"] = {
                    "periodo": f"{tano}/{tmes}",
                    "total": len(data),
                    "chaves": list(data[0].keys()),
                    "amostra": data[:3],
                }
                break
    except Exception as e:
        print(f"  TCE {tano}/{tmes} erro:", e, flush=True)
        OUT.setdefault("TCE despesas", {})["erro"] = str(e)

# Grava o schema capturado para leitura confiável via git
os.makedirs("docs/data", exist_ok=True)
with open("docs/data/_diag_schema.json", "w", encoding="utf-8") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=2)
print("\n===== fim do diagnóstico (schema em docs/data/_diag_schema.json) =====", flush=True)
