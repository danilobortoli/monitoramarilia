"""
Diagnóstico TEMPORÁRIO de schema das APIs (TCE-SP e SICONFI).

Imprime no log do job os nomes reais dos campos retornados, para corrigir
o mapeamento dos coletores. Não faz parte do produto — pode ser removido
após o ajuste.
"""
import datetime
import json

import requests

S = requests.Session()
S.headers.update({"Accept": "application/json", "User-Agent": "MonitoraMarilia/diag"})


def amostra(titulo, items, n=2):
    print(f"\n===== {titulo} =====", flush=True)
    if not items:
        print("  (sem dados / falha)")
        return
    print(f"  total: {len(items)}")
    print(f"  chaves: {list(items[0].keys())}")
    for it in items[:n]:
        print("  amostra:", json.dumps(it, ensure_ascii=False)[:600])


# 1) TCE-SP — despesas brutas (descobrir nomes de valor/fornecedor/evento)
ano = datetime.date.today().year
for tentativa_ano in (ano, ano - 1):
    achou = False
    for mes in (3, 2, 1, 12, 11):
        try:
            r = S.get(
                f"https://transparencia.tce.sp.gov.br/api/json/despesas/marilia/{tentativa_ano}/{mes}",
                timeout=60,
            )
            print(f"TCE despesas {tentativa_ano}/{mes} -> HTTP {r.status_code}", flush=True)
            if r.ok:
                data = r.json()
                data = data if isinstance(data, list) else [data]
                if data:
                    amostra(f"TCE despesas {tentativa_ano}/{mes}", data)
                    achou = True
                    break
        except Exception as e:
            print(f"TCE erro {tentativa_ano}/{mes}:", e)
    if achou:
        break


def siconfi(endpoint, params, titulo, filtro=("CORRENTE LÍQUIDA", "RCL", "PESSOAL")):
    try:
        r = S.get(
            f"https://apidatalake.tesouro.gov.br/ords/siconfi/tt/{endpoint}",
            params=params, timeout=60,
        )
        print(f"\n{titulo} -> HTTP {r.status_code}", flush=True)
        if r.ok:
            items = r.json().get("items", [])
            print(f"  total: {len(items)}")
            if items:
                print(f"  chaves: {list(items[0].keys())}")
            for it in items:
                conta = (it.get("conta") or "").upper()
                if any(f in conta for f in filtro):
                    print("   >>>", json.dumps(
                        {k: it.get(k) for k in ("cod_conta", "conta", "coluna", "valor")},
                        ensure_ascii=False))
    except Exception as e:
        print(f"{titulo} erro:", e)


# 2) SICONFI RREO Anexo 03 (RCL) — período conhecido do ano anterior
siconfi("rreo",
        {"an_exercicio": ano - 1, "nr_periodo": 6, "co_tipo_demonstrativo": "RREO",
         "no_anexo": "RREO-Anexo 03", "id_ente": "3529005"},
        f"SICONFI RREO Anexo03 {ano-1}/bim6 (RCL)")

# 3) SICONFI RGF Anexo 01 (Despesa com pessoal) — período conhecido
siconfi("rgf",
        {"an_exercicio": ano - 1, "nr_periodo": 3, "co_tipo_demonstrativo": "RGF",
         "no_anexo": "RGF-Anexo 01", "co_esfera": "M", "co_poder": "E", "id_ente": "3529005"},
        f"SICONFI RGF Anexo01 {ano-1}/quad3 (Pessoal)")

print("\n===== fim do diagnóstico =====", flush=True)
