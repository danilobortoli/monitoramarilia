"""
Diagnóstico TEMPORÁRIO de schema das APIs (SICONFI e TCE-SP).

Imprime no log do job os nomes reais dos campos retornados, para corrigir
o mapeamento dos coletores. Resiliente a throttling: SICONFI primeiro e
TCE-SP com timeout curto. Pode ser removido após o ajuste.
"""
import datetime
import json

import requests

S = requests.Session()
S.headers.update({"Accept": "application/json", "User-Agent": "MonitoraMarilia/diag"})
ano = datetime.date.today().year


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
            if items:
                print(f"  chaves: {list(items[0].keys())}")
                print(f"  colunas distintas: {sorted(set(i.get('coluna','') for i in items))[:12]}")
            for it in items:
                conta = (it.get("conta") or "").upper()
                if any(f in conta for f in filtro):
                    print("   >>>", json.dumps(
                        {k: it.get(k) for k in ("cod_conta", "conta", "coluna", "valor")},
                        ensure_ascii=False))
    except Exception as e:
        print(f"{titulo} erro:", e, flush=True)


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
                break
    except Exception as e:
        print(f"  TCE {tano}/{tmes} erro:", e, flush=True)

print("\n===== fim do diagnóstico =====", flush=True)
