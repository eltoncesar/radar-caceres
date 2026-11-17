"""Confere uma amostra de propostas do site com as páginas oficiais do SAPL.

Uso:  python3 conferencia/conferir_amostra.py [tamanho_da_amostra]

Para cada proposta sorteada, abre a página pública da matéria e a aba de
autoria no SAPL (as mesmas que o cidadão vê) e compara com os dados do site:
tipo, número, ano, data de apresentação, resumo e autores.
O sorteio pega propostas de todos os vereadores, para usar a mesma régua.
"""
import html
import json
import os
import random
import re
import sys
import time
import unicodedata
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAPL = "https://sapl.caceres.mt.leg.br"
HEADERS = {"User-Agent": "RadarCaceres/0.1 (conferencia de dados; coleta lenta)"}


def carregar(nome):
    with open(os.path.join(RAIZ, "dados", "brutos", f"{nome}.json"), encoding="utf-8") as f:
        return json.load(f)


def texto_da_pagina(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        bruto = resp.read().decode("utf-8", "replace")
    bruto = re.sub(r"<(script|style)\b.*?</\1>", " ", bruto, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", "\n", bruto))


def norm(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def campo(texto, rotulo):
    m = re.search(rf"\n\s*{re.escape(rotulo)}\s*\n+\s*([^\n]+)", texto)
    return m.group(1).strip() if m else ""


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    tipos = {t["id"]: t["descricao"] for t in carregar("tipos_materia")}
    autores = {a["id"]: a for a in carregar("autores")}
    parl = {a["id"] for a in autores.values() if a["tipo"] == 1}
    mandatos = {m["parlamentar"] for m in carregar("mandatos")}
    materias = [m for ano in ("2025", "2026") for m in carregar(f"materias_{ano}")
                if any(a in parl and autores[a]["object_id"] in mandatos for a in m["autores"])]

    # Sorteio estratificado: pelo menos uma proposta de cada vereador com propostas.
    random.seed(20261117)
    por_autor = {}
    for m in materias:
        for a in m["autores"]:
            if a in parl:
                por_autor.setdefault(a, []).append(m)
    amostra = {random.choice(lista)["id"]: None for lista in por_autor.values()}
    resto = [m for m in materias if m["id"] not in amostra]
    for m in random.sample(resto, max(0, n - len(amostra))):
        amostra[m["id"]] = None
    porid = {m["id"]: m for m in materias}

    ok, problemas = 0, []
    for mid in amostra:
        m = porid[mid]
        pag = texto_da_pagina(f"{SAPL}/materia/{mid}")
        time.sleep(0.6)
        # A aba de autoria é dividida em páginas quando há muitos autores.
        aut = ""
        for pagina in range(1, 6):
            parte = texto_da_pagina(f"{SAPL}/materia/{mid}/autoria?page={pagina}")
            time.sleep(0.6)
            aut += parte
            total = re.search(r"Total de Autorias:\s*(\d+)", parte)
            if not total or int(total.group(1)) <= 10 * pagina:
                break
        erros = []
        total = re.search(r"Total de Autorias:\s*(\d+)", aut)
        if total and int(total.group(1)) != len(m["autores"]):
            erros.append(f"total de autores: site={len(m['autores'])} oficial={total.group(1)}")
        if norm(campo(pag, "Tipo de Matéria Legislativa")) != norm(tipos[m["tipo"]]):
            erros.append(f"tipo: site={tipos[m['tipo']]!r} oficial={campo(pag, 'Tipo de Matéria Legislativa')!r}")
        if campo(pag, "Número") != str(m["numero"]) or campo(pag, "Ano") != str(m["ano"]):
            erros.append(f"número/ano: site={m['numero']}/{m['ano']} oficial={campo(pag, 'Número')}/{campo(pag, 'Ano')}")
        data_site = "/".join(reversed((m["data_apresentacao"] or "").split("-")))
        if campo(pag, "Data de Apresentação") != data_site:
            erros.append(f"data: site={data_site} oficial={campo(pag, 'Data de Apresentação')}")
        if norm(m["ementa"])[:120] not in norm(pag):
            erros.append("resumo diferente do oficial")
        for a in m["autores"]:
            if norm(autores[a]["nome"]) not in norm(aut):
                erros.append(f"autor {autores[a]['nome']} não aparece na aba de autoria")
        nome = f"{tipos[m['tipo']]} nº {m['numero']}/{m['ano']} ({SAPL}/materia/{mid})"
        if erros:
            problemas.append((nome, erros))
        else:
            ok += 1
        print(("OK  " if not erros else "ERRO") + " " + nome, file=sys.stderr)

    print(f"\nConferidas {len(amostra)} propostas de {len(por_autor)} vereadores: {ok} batem.")
    for nome, erros in problemas:
        print(f"- {nome}: " + "; ".join(erros))


if __name__ == "__main__":
    main()
