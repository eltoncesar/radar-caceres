"""Avisa quando aparece uma Portaria ou Ato sobre licença, convocação ou retorno
de vereador que ainda não foi revisado em dados/licencas.json.

Uso:  python3 conferencia/novas_portarias.py [arquivo_de_saida.md]

Imprime (e grava, se pedido) uma lista em Markdown. Não altera nada: a tabela
de licenças é revisada à mão, lendo cada Portaria. Sai com código 0 sempre;
quem decide o que fazer com a lista é o robô (abre um aviso no GitHub).
"""
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAPL = "https://sapl.caceres.mt.leg.br"
TIPOS = {"Portaria", "Ato da Mesa Diretora", "Ato da Presidência"}
ASSUNTO = re.compile(r"licen|afast|convoca|retorno|cessa|recondu|posse|reassun|deputad|secret[aá]ri[oa] municipal", re.I)
QUEM = re.compile(r"vereador|vereadora|verean[cç]a|suplente|mandato|deputad", re.I)
FORA = re.compile(r"comiss|fiscal|servidor|f[eé]rias|contrato|estagi|assessor", re.I)


def carregar(caminho):
    with open(os.path.join(RAIZ, caminho), encoding="utf-8") as f:
        return json.load(f)


def main():
    tipos = {t["id"]: t["descricao"] for t in carregar("dados/brutos/tipos_norma.json")}
    lic = carregar("dados/licencas.json")
    conhecidas = {nid for grupo in ("licencas", "suplentes") for item in lic[grupo] for nid in item["normas"].values()}
    conhecidas |= {r["id"] for r in lic.get("normas_revisadas_sem_efeito", [])}

    novas = []
    for n in carregar("dados/brutos/normas.json"):
        ementa = re.sub(r"\s+", " ", n.get("ementa") or "")
        if tipos.get(n["tipo"]) not in TIPOS or n["id"] in conhecidas:
            continue
        if ASSUNTO.search(ementa) and QUEM.search(ementa) and not FORA.search(ementa):
            novas.append(f"- [{tipos[n['tipo']]} {n['numero']}/{n['ano']}]({SAPL}/norma/{n['id']}) "
                         f"({n['data']}): {ementa[:220]}")

    texto = ""
    if novas:
        texto = ("Apareceram atos da Câmara sobre licença, convocação ou retorno de vereador que ainda não estão em "
                 "`dados/licencas.json`. Até serem revisados, os dias de licença podem aparecer como falta no site.\n\n"
                 + "\n".join(novas)
                 + "\n\nPara cada um: leia o ato, atualize `dados/licencas.json` (ou registre em "
                   "`normas_revisadas_sem_efeito` se não mudar nada) e feche este aviso.")
    print(texto or "Nenhum ato novo de licença para revisar.")
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as f:
            f.write(texto)


if __name__ == "__main__":
    main()
