"""
Diagnóstico TEMPORÁRIO de schema das APIs (SICONFI e TCE-SP).

Grava docs/data/_diag_schema.json com os campos reais retornados, para
corrigir o mapeamento dos coletores. Pode ser removido após o ajuste.
"""
import datetime
import json
import os
import time

import requests

S = requests.Session()
S.headers.update({"Accept": "application/json", "User-Agent": "MonitoraMarilia/diag"})
ano = datetime.date.today().year
OUT = {}


def siconfi(endpoint, params, titulo, filtro):
    try:
        r = S.get(f"https://apidatalake.tesouro.gov.br/ords/siconfi/tt/{endpoint}",
                  params=params, timeout=45)
        items = r.json().get("items", []) if r.ok else []
        print(f"\n{titulo} -> HTTP {r.status_code} | itens: {len(items)}", flush=True)
        info = {"http": r.status_code, "total": len(items)}
        if items:
            info["chaves"] = list(items[0].keys())
            info["amostra_crua"] = items[:2]
            info["colunas"] = sorted(set((i.get("coluna") or "") for i in items))
            achados = []
            for it in items:
                conta = (it.get("conta") or "").upper()
                if any(f in conta for f in filtro):
                    achados.append({k: it.get(k) for k in ("cod_conta", "conta", "coluna", "valor")})
            info["achados"] = achados[:60]
        OUT[titulo] = info
        return len(items) > 0
    except Exception as e:
        print(f"{titulo} erro:", e, flush=True)
        OUT[titulo] = {"erro": str(e)}
        return False


# 1) RCL (RREO Anexo 03) — confirmação
siconfi("rreo",
        {"an_exercicio": ano - 1, "nr_periodo": 6, "co_tipo_demonstrativo": "RREO",
         "no_anexo": "RREO-Anexo 03", "id_ente": "3529005"},
        f"RREO Anexo03 {ano-1}/bim6 (RCL)", ("CORRENTE LÍQUIDA", "RCL"))

# 2) RGF Anexo 01 (Pessoal) — tenta vários períodos até achar dados
for ay, q in ((ano - 1, 3), (ano - 1, 2), (ano - 2, 3)):
    ok = siconfi("rgf",
                 {"an_exercicio": ay, "nr_periodo": q, "co_tipo_demonstrativo": "RGF",
                  "no_anexo": "RGF-Anexo 01", "co_esfera": "M", "co_poder": "E",
                  "id_ente": "3529005"},
                 f"RGF Anexo01 {ay}/quad{q} (Pessoal)",
                 ("DESPESA TOTAL COM PESSOAL", "PESSOAL", "RECEITA CORRENTE LÍQUIDA"))
    if ok:
        break

# 3) TCE-SP despesas — timeout generoso + retry; captura amostra crua
print("\n===== TCE-SP despesas =====", flush=True)
tce_ok = False
for tano, tmes in ((ano, 2), (ano, 1), (ano - 1, 12), (ano - 1, 11)):
    for tentativa in range(2):
        try:
            r = S.get(f"https://transparencia.tce.sp.gov.br/api/json/despesas/marilia/{tano}/{tmes}",
                      timeout=50)
            print(f"  TCE {tano}/{tmes} (try {tentativa}) -> HTTP {r.status_code}", flush=True)
            if r.ok:
                data = r.json()
                data = data if isinstance(data, list) else [data]
                if data:
                    OUT["TCE despesas"] = {"periodo": f"{tano}/{tmes}", "total": len(data),
                                           "chaves": list(data[0].keys()), "amostra": data[:3]}
                    print("  chaves:", list(data[0].keys()), flush=True)
                    tce_ok = True
                    break
        except Exception as e:
            print(f"  TCE {tano}/{tmes} erro:", e, flush=True)
            OUT.setdefault("TCE despesas", {})["erro"] = str(e)
            time.sleep(2)
    if tce_ok:
        break

os.makedirs("docs/data", exist_ok=True)
with open("docs/data/_diag_schema.json", "w", encoding="utf-8") as f:
    json.dump(OUT, f, ensure_ascii=False, indent=2)
print("\n===== fim do diagnóstico =====", flush=True)
