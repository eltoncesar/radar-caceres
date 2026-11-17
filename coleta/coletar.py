"""Coleta os dados oficiais da Câmara Municipal de Cáceres-MT pela API pública do SAPL.

Uso:  python3 coleta/coletar.py [pasta_destino]   (padrão: dados/brutos)

- Só usa a API pública (https://sapl.caceres.mt.leg.br/api/), sem login.
- Identifica-se como robô e espera entre as páginas para não pesar no servidor.
- Remove campos internos que não interessam ao cidadão (IP e usuário de quem
  registrou a votação no sistema).
- Se alguma coleta vier vazia ou bem menor que a anterior, para sem gravar nada:
  o site continua com a última versão boa.
"""
import json
import os
import sys
import time
import urllib.request

API = "https://sapl.caceres.mt.leg.br/api/"
HEADERS = {
    "User-Agent": "RadarCaceres/0.1 (robo de dados abertos; coleta lenta)",
    "Accept": "application/json",
}
LEGISLATURA_ATUAL = 3  # 20ª legislatura (2025-2028)
CAMPOS_REMOVIDOS = {"ip", "user"}

CONJUNTOS = {
    "parlamentares": "parlamentares/parlamentar/",
    "mandatos": f"parlamentares/mandato/?legislatura={LEGISLATURA_ATUAL}",
    "filiacoes": "parlamentares/filiacao/",
    "partidos": "parlamentares/partido/",
    "autores": "base/autor/",
    "tipos_materia": "materia/tipomaterialegislativa/",
    "tipos_sessao": "sessao/tiposessaoplenaria/",
    "tipos_resultado": "sessao/tiporesultadovotacao/",
    "tipos_justificativa": "sessao/tipojustificativa/",
    "sessoes": f"sessao/sessaoplenaria/?legislatura={LEGISLATURA_ATUAL}",
    "materias_2025": "materia/materialegislativa/?ano=2025",
    "materias_2026": "materia/materialegislativa/?ano=2026",
    "autorias": "materia/autoria/",
    "presenca_abertura": "sessao/sessaoplenariapresenca/",
    "presenca_ordem_dia": "sessao/presencaordemdia/",
    "justificativas_ausencia": "sessao/justificativaausencia/",
    "votacoes": "sessao/registrovotacao/",
    "votos_nominais": "sessao/votoparlamentar/",
    "mesas": "parlamentares/mesadiretora/",
    "composicao_mesa": "parlamentares/composicaomesa/",
    "cargos_mesa": "parlamentares/cargomesa/",
    "status_tramitacao": "materia/statustramitacao/",
    "tramitacoes": "materia/tramitacao/?data_tramitacao__gte=2025-01-01",
}


def baixar_json(url):
    for tentativa in range(4):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except Exception as erro:  # rede instável: tenta de novo, devagar
            print(f"  tentativa {tentativa + 1} falhou: {erro}", file=sys.stderr)
            time.sleep(5 * (tentativa + 1))
    raise RuntimeError(f"Não consegui baixar {url}")


def baixar_tudo(caminho):
    sep = "&" if "?" in caminho else "?"
    # "o=id" fixa a ordem: sem isso o SAPL embaralha as páginas e a coleta
    # repete umas linhas e perde outras.
    url = f"{API}{caminho}{sep}page_size=100&o=id"
    itens = []
    while url:
        dados = baixar_json(url)
        for item in dados["results"]:
            itens.append({k: v for k, v in item.items() if k not in CAMPOS_REMOVIDOS})
        proxima = dados["pagination"].get("links", {}).get("next")
        url = proxima.replace("http://", "https://") if proxima else None
        time.sleep(0.5)
    return itens


def main():
    destino = sys.argv[1] if len(sys.argv) > 1 else "dados/brutos"
    os.makedirs(destino, exist_ok=True)
    novos = {}
    for nome, caminho in CONJUNTOS.items():
        novos[nome] = baixar_tudo(caminho)
        print(f"{nome}: {len(novos[nome])}")

    problemas = []
    for nome, itens in novos.items():
        arquivo = os.path.join(destino, f"{nome}.json")
        if not itens and nome != "votos_nominais":
            problemas.append(f"{nome} veio vazio")
        elif len({i["id"] for i in itens}) != len(itens):
            problemas.append(f"{nome} veio com linhas repetidas")
        elif os.path.exists(arquivo):
            anterior = len(json.load(open(arquivo, encoding="utf-8")))
            if len(itens) < anterior * 0.9:
                problemas.append(f"{nome} caiu de {anterior} para {len(itens)}")
    if problemas:
        print("Coleta estranha, nada foi gravado:\n- " + "\n- ".join(problemas), file=sys.stderr)
        sys.exit(1)

    for nome, itens in novos.items():
        with open(os.path.join(destino, f"{nome}.json"), "w", encoding="utf-8") as f:
            json.dump(itens, f, ensure_ascii=False, indent=0)
    with open(os.path.join(destino, "_coleta.json"), "w", encoding="utf-8") as f:
        totais = {nome: len(itens) for nome, itens in novos.items()}
        json.dump({"data": time.strftime("%Y-%m-%d"), "totais": totais}, f, ensure_ascii=False, indent=1)
    print(f"Gravado em {destino}")

    baixar_fotos(novos, os.path.join(os.path.dirname(os.path.abspath(destino)), "fotos"))


def baixar_fotos(dados, pasta):
    """Baixa e reduz a foto oficial de quem tem mandato na legislatura atual."""
    import io
    from PIL import Image

    os.makedirs(pasta, exist_ok=True)
    com_mandato = {m["parlamentar"] for m in dados["mandatos"]}
    for p in dados["parlamentares"]:
        if p["id"] not in com_mandato or not p.get("fotografia"):
            continue
        url = p["fotografia"].replace("http://", "https://")
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=60) as resp:
                img = Image.open(io.BytesIO(resp.read())).convert("RGB")
        except Exception as erro:
            print(f"  foto de {p['nome_parlamentar']} falhou: {erro}", file=sys.stderr)
            continue
        # O SAPL guarda o recorte do rosto escolhido pela Câmara ("x1,y1,x2,y2").
        try:
            caixa = tuple(int(n) for n in (p.get("cropping") or "").split(","))
            if len(caixa) == 4 and caixa[2] > caixa[0] and caixa[3] > caixa[1]:
                img = img.crop(caixa)
        except ValueError:
            pass
        lado = min(img.size)
        esq, topo = (img.width - lado) // 2, (img.height - lado) // 2
        img = img.crop((esq, topo, esq + lado, topo + lado)).resize((176, 176), Image.LANCZOS)
        img.save(os.path.join(pasta, f"{p['id']}.jpg"), "JPEG", quality=82, optimize=True)
        time.sleep(0.5)
    print(f"Fotos em {pasta}")


if __name__ == "__main__":
    main()
