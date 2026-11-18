"""Gera o site estático do Radar Cáceres a partir de dados/brutos.

Uso:  python3 gerar/gerar_site.py   (gera a pasta site/)
"""
import collections
import datetime
import html
import json
import os
import re
import shutil
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from resumo import resumo as resumo_legivel  # noqa: E402
from classificar import GRUPOS, ORDEM as ORDEM_GRUPOS, REGRA_EXPLICADA, classificar  # noqa: E402
import pagina_inicial  # noqa: E402
import pagina_v2  # noqa: E402
import situacao as sit  # noqa: E402
import presenca  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRUTOS = os.path.join(RAIZ, "dados", "brutos")
FOTOS = os.path.join(RAIZ, "dados", "fotos")
SAIDA = os.path.join(RAIZ, "site")
SAPL = "https://sapl.caceres.mt.leg.br"
ANOS = ("2025", "2026")
TIPO_AUTOR_PARLAMENTAR = 1

# Explicação em linguagem simples de cada tipo de proposta.
EXPLICA_TIPO = {
    "Indicação": "Pedido para a Prefeitura fazer algo, como consertar rua, trocar lâmpada ou limpar terreno.",
    "Requerimento": "Pedido formal de informação ou de providência, geralmente à Prefeitura ou a outro órgão.",
    "Moção": "Manifestação em nome da Câmara: aplauso, pesar, apoio ou repúdio.",
    "Projeto de Decreto Legislativo": "Em Cáceres, quase sempre é para dar título de cidadão ou diploma de honra.",
    "Projeto de Lei": "Proposta de uma nova lei municipal ou de mudança numa lei existente.",
    "Projeto de Lei Complementar": "Proposta de lei sobre temas que a Lei Orgânica exige que sejam tratados assim.",
    "Projeto de Resolução": "Regras internas do funcionamento da própria Câmara.",
    "Proposta de Emenda à Lei Orgânica": "Mudança na Lei Orgânica, que funciona como a Constituição do município.",
    "Emenda Parlamentar": "Proposta de mudança no texto de outro projeto.",
}


def carregar(nome):
    with open(os.path.join(BRUTOS, f"{nome}.json"), encoding="utf-8") as f:
        return json.load(f)


def slug(texto):
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def limpar(texto):
    texto = re.sub(r"\s+", " ", texto or "").strip()
    return texto.strip("“”‘’\"'´` ").strip()


def esc(texto):
    return html.escape(str(texto), quote=True)


def data_br(iso):
    return datetime.date.fromisoformat(iso).strftime("%d/%m/%Y") if iso else ""


def nome_exibicao(nome):
    """'PASTOR JÚNIOR' -> 'Pastor Júnior'. O SAPL guarda os nomes em caixa alta."""
    pequenas = {"da", "de", "do", "das", "dos", "e"}
    return " ".join(p if p in pequenas else p[:1].upper() + p[1:] for p in (nome or "").lower().split())


def rotulo_cargo(c):
    """'1° SECRETÁRIO(A)' -> '1º secretário(a) da Câmara'."""
    if not c:
        return ""
    c = c.replace("°", "º").lower()
    return c[:1].upper() + c[1:] + " da Câmara"


def montar_dados():
    parlamentares = {p["id"]: p for p in carregar("parlamentares")}
    partidos = {p["id"]: p for p in carregar("partidos")}
    tipos = {t["id"]: t["descricao"] for t in carregar("tipos_materia")}
    autor_para_parl = {a["id"]: a["object_id"] for a in carregar("autores") if a["tipo"] == TIPO_AUTOR_PARLAMENTAR}
    materias = {m["id"]: m for ano in ANOS for m in carregar(f"materias_{ano}")}

    filiacao_atual = {}
    for f in sorted(carregar("filiacoes"), key=lambda f: f["data"] or ""):
        if not f["data_desfiliacao"]:
            filiacao_atual[f["parlamentar"]] = partidos.get(f["partido"], {}).get("sigla", "")

    status_nome = {x["id"]: x["descricao"] for x in carregar("status_tramitacao")}
    ultima = sit.ultimas(carregar("tramitacoes"), status_nome)

    propostas = collections.defaultdict(list)
    for a in carregar("autorias"):
        pid = autor_para_parl.get(a["autor"])
        m = materias.get(a["materia"])
        if pid is None or m is None:
            continue
        propostas[pid].append({
            "id": m["id"],
            "tipo": tipos[m["tipo"]],
            "numero": m["numero"],
            "ano": m["ano"],
            "data": m["data_apresentacao"],
            "ementa": limpar(m["ementa"]),
            "primeiro_autor": a["primeiro_autor"],
            "grupo": classificar(tipos[m["tipo"]], m["ementa"]),
            "status": ultima.get(m["id"], (None, ""))[1],
            "status_data": ultima.get(m["id"], (None, ""))[0],
            "situacao": sit.situacao(tipos[m["tipo"]], ultima.get(m["id"], (None, ""))[1]),
        })

    # Cargo na Mesa Diretora mais recente (a de maior id é a do ano corrente).
    cargos_mesa = {c["id"]: c["descricao"] for c in carregar("cargos_mesa")}
    mesa_atual = max(m["id"] for m in carregar("mesas"))
    cargo = {c["parlamentar"]: cargos_mesa[c["cargo"]] for c in carregar("composicao_mesa") if c["mesa_diretora"] == mesa_atual}

    with open(os.path.join(RAIZ, "dados", "licencas.json"), encoding="utf-8") as f:
        licencas = json.load(f)
    with open(os.path.join(BRUTOS, "_coleta.json"), encoding="utf-8") as f:
        hoje = json.load(f)["data"]
    tipos_sessao = {t["id"]: t["nome"] for t in carregar("tipos_sessao")}
    pres = presenca.calcular(carregar("sessoes"), tipos_sessao,
                             [carregar("presenca_abertura"), carregar("presenca_ordem_dia")],
                             carregar("justificativas_ausencia"), carregar("mandatos"), licencas, hoje)

    # Discursos na tribuna (oradores registrados no SAPL), só nesta legislatura.
    sessoes_leg = {x["id"]: x for x in carregar("sessoes")}
    discursos = collections.defaultdict(list)
    for o in carregar("oradores"):
        se = sessoes_leg.get(o["sessao_plenaria"])
        if not se:
            continue
        link = (o.get("url_discurso") or se.get("url_video") or f'{SAPL}/sessao/{se["id"]}').replace("http://", "https://")
        discursos[o["parlamentar"]].append({"data": se["data_inicio"], "sessao": se["id"], "link": link,
                                            "video": bool(o.get("url_discurso") or se.get("url_video"))})

    vereadores = []
    for mand in carregar("mandatos"):
        p = parlamentares[mand["parlamentar"]]
        email = (p.get("email") or "").strip()
        lista = sorted(propostas[p["id"]], key=lambda x: (x["data"] or "", x["id"]), reverse=True)
        vereadores.append({
            "id": p["id"],
            "nome": nome_exibicao(p["nome_parlamentar"]),
            "nome_completo": p["nome_completo"],
            "slug": slug(p["nome_parlamentar"]),
            "partido": filiacao_atual.get(p["id"], ""),
            "foto": os.path.exists(os.path.join(FOTOS, f"{p['id']}.jpg")),
            "titular": mand["titular"],
            "inicio": mand["data_inicio_mandato"],
            "fim": mand["data_fim_mandato"],
            "observacao": limpar(mand.get("observacao")),
            # Só contato público de gabinete: e-mail institucional e telefone fixo.
            "email": email if email.endswith("@caceres.mt.leg.br") else "",
            "telefone": (p.get("telefone") or "").strip(),
            "propostas": lista,
            "cargo": rotulo_cargo(cargo.get(p["id"], "")),
            "presenca": pres[p["id"]],
            "discursos": sorted(discursos[p["id"]], key=lambda d: d["data"], reverse=True),
        })
    vereadores.sort(key=lambda v: (not v["titular"], v["nome"]))
    return vereadores


CABECA = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<meta name="description" content="{descricao}">
<meta name="theme-color" content="#F8FAFD">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Roboto+Flex:opsz,wght@8..144,400..800&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400..500,0..1,0&icon_names=add_road,arrow_back,block,celebration,check,chevron_right,cleaning_services,close,construction,contact_support,directions_bus,expand_more,flood,forest,gavel,grid_view,help,landscape,lightbulb,local_hospital,location_on,mark_email_read,more_horiz,open_in_new,park,pending,person,person_search,play_circle,radar,record_voice_over,schedule,school,search,table_rows,traffic,unfold_more,verified,water_drop&display=block" rel="stylesheet">
<link rel="stylesheet" href="{base}estilo.css">
</head>
<body>
<div class="barra-a11y" role="region" aria-label="Atalhos e fonte dos dados"><div class="container">
<nav aria-label="Atalhos de acessibilidade"><a href="{base}index.html#panorama" accesskey="1">Panorama <kbd>Alt+1</kbd></a><a href="{base}index.html#busca" accesskey="2">Seu bairro <kbd>Alt+2</kbd></a><a href="{base}index.html#problemas" accesskey="3">O problema que não some <kbd>Alt+3</kbd></a><a href="{base}index.html#vereadores" accesskey="4">Vereadores <kbd>Alt+4</kbd></a></nav>
<span class="fonte-dados">Dados públicos do SAPL · Câmara Municipal de Cáceres-MT</span></div></div>
<header class="cabecalho"><div class="container">
<a href="{base}index.html" class="marca"><span class="marca-ic" aria-hidden="true"><span class="ms">radar</span></span>
<span><span class="marca-tit">Radar Cáceres</span><span class="marca-sub">Legislatura 2025–2028</span></span></a>
<nav class="menu" aria-label="Principal"><a href="{base}index.html#busca">Por bairro</a><a href="{base}index.html#problemas">O que não some</a><a href="{base}index.html#vereadores">Vereadores</a><a href="{base}sobre.html">Como funciona</a></nav>
<a class="gatilho-busca" id="abrir-busca" href="{base}index.html#buscar" aria-label="Buscar vereador, bairro ou rua"><span class="ms" aria-hidden="true">search</span><span class="rotulo">Buscar bairro ou vereador</span><kbd>/</kbd></a>
</div></header>
<main id="conteudo">
"""

RODAPE = """</main>
<footer class="rodape-site" id="rodape"><div class="container">
<div class="rodape-grade"><div><p class="rodape-tit">Radar Cáceres</p>
<p>Ferramenta cívica de código aberto para aproximar o cidadão de Cáceres do dia a dia da Câmara Municipal. Todos os dados
vêm do <a href="{sapl}">SAPL da Câmara</a>, coletados automaticamente toda madrugada.</p></div>
<div><p class="rodape-tit">Como contamos</p>
<p>Indicações são pedidos de melhoria; requerimentos, perguntas e cobranças; moções e títulos, homenagens; projetos de lei e de
resolução, propostas de lei. <a href="{base}sobre.html">Veja a regra completa</a>.</p></div></div>
<p class="rodape-nota">Última conferência: {coleta} · Nenhuma filiação partidária ·
Viu um erro? <a href="https://github.com/eltoncesar/radar-caceres/issues">Avise aqui</a> · <a href="https://github.com/eltoncesar/radar-caceres">Código e dados abertos</a></p>
</div></footer>
</body>
</html>
"""


def pagina(titulo, descricao, corpo, base, coleta, larga=False):
    if not larga:
        corpo = f'<div class="container pagina">{corpo}</div>'
    return (CABECA.format(titulo=esc(titulo), descricao=esc(descricao), base=base)
            + corpo + RODAPE.format(sapl=SAPL, coleta=coleta, base=base))

def foto(v, base):
    if v["foto"]:
        return f'<img class="foto" src="{base}fotos/{v["id"]}.jpg" alt="" width="88" height="88" loading="lazy">'
    return '<span class="foto vazia" aria-hidden="true"></span>'


def periodo(v):
    if v["titular"]:
        return "Titular"
    # Períodos tirados das Portarias (dados/licencas.json), não do SAPL, cujas datas não batem.
    ex = v.get("presenca", {}).get("exercicio")
    if not ex:
        return "Suplente que assumiu uma vaga"
    trechos = " e ".join(f"{data_br(a)} a {data_br(b)}" for a, b in ex["periodos"])
    return f"Suplente em exercício de {trechos}, no lugar de {ex['no_lugar_de'].title().replace('; Depois', '; depois')}"


AVISO_VOTO = """<aside class="aviso"><strong>Por que não mostramos como cada vereador votou?</strong>
A Câmara não registra no sistema oficial o voto de cada vereador desde agosto de 2020.
Hoje só aparece o resultado geral, por exemplo “aprovado por unanimidade”.</aside>
"""

AVISO_PRESENCA = """<aside class="aviso"><strong>E a presença nas sessões?</strong>
Ainda não mostramos. Os registros oficiais de presença têm falhas, como licenças que não aparecem.
Só vamos publicar quando pudermos conferir cada número.</aside>
"""


def gerar_index(vereadores, coleta):
    corpo = pagina_v2.gerar(vereadores, coleta, esc, foto, periodo, SAPL, ANOS, EXEMPLOS_LUGAR, data_br)
    return pagina("Radar Cáceres — o que fazem os vereadores de Cáceres-MT",
                  "O que cada vereador de Cáceres-MT propôs, pedido por pedido, com dados oficiais da Câmara.",
                  corpo, "", coleta, larga=True)

def gerar_vereador(v, coleta):
    por_grupo = collections.defaultdict(list)
    for p in v["propostas"]:
        por_grupo[p["grupo"]].append(p)
    grupos = [g for g in ORDEM_GRUPOS if por_grupo[g]]
    total = len(v["propostas"])
    principal = sum(p["primeiro_autor"] for p in v["propostas"])

    resumo = "".join(
        f'<li><a class="g-{g}" href="#{g}"><b>{len(por_grupo[g])}</b><span>{esc(GRUPOS[g][0])}</span></a></li>' for g in grupos)
    blocos = []
    for g in grupos:
        itens = "".join(
            f'<li><a href="{SAPL}/materia/{p["id"]}">{esc(p["tipo"])} nº {p["numero"]}/{p["ano"]}</a>'
            f'<span class="data">{data_br(p["data"])}{"" if p["primeiro_autor"] else " · coautor"}</span>'
            f'{pagina_inicial.etiqueta_situacao(p, esc)}'
            f'<p>{esc(resumo_legivel(p["ementa"])) or "<em>Sem resumo no sistema oficial.</em>"}</p></li>'
            for p in por_grupo[g])
        blocos.append(f'<details id="{g}"><summary>{esc(GRUPOS[g][0])} <span class="contagem">{len(por_grupo[g])}</span></summary>'
                      f'<p class="explica">{esc(GRUPOS[g][1])} <a href="../sobre.html#regra">Como separamos</a>.</p>'
                      f'<ol class="propostas">{itens}</ol></details>')

    contato = []
    if v["email"]:
        contato.append(f'<a href="mailto:{esc(v["email"])}">{esc(v["email"])}</a>')
    if v["telefone"]:
        contato.append(f'<a href="tel:{esc(re.sub(r"[^0-9+]", "", v["telefone"]))}">{esc(v["telefone"])}</a>')

    corpo = f"""<p class="voltar"><a href="../index.html#vereadores">← Todos os vereadores</a></p>
<div class="perfil">{foto(v, "../")}<div><h1>{esc(v["nome"])}</h1>
<p class="sub">{esc(v["nome_completo"])}</p>
<p class="sub">{esc(v["partido"])}{" · " if v["partido"] else ""}{esc(periodo(v))}</p>
{f'<p class="sub">Gabinete: {" · ".join(contato)}</p>' if contato else ""}
<p class="sub"><a href="{SAPL}/parlamentar/{v["id"]}">Ficha oficial na Câmara</a></p></div></div>
<div class="destaque"><p><b>{total}</b> propostas em {" e ".join(ANOS)}</p>
<p class="sub">{principal} como autor principal · {total - principal} assinadas junto com outros vereadores</p>
{pagina_inicial.resumo_situacao(v["propostas"], esc)}</div>
{pagina_inicial.bloco_presenca(v, esc, data_br, SAPL)}
{pagina_inicial.bloco_discursos(v, esc, data_br)}
{f'<ul class="resumo">{resumo}</ul><p class="sub">Toque num grupo para ler proposta por proposta.</p>' if grupos else "<p>Nenhuma proposta registrada no período.</p>"}
{"".join(blocos)}
<details class="legenda"><summary>O que quer dizer cada situação</summary><dl class="glossario">
{"".join(f"<dt>{esc(sit.ROTULO[k])}</dt><dd>{esc(sit.EXPLICA[k])}</dd>" for k in (sit.RESPONDIDO, sit.AGUARDANDO, sit.TRAMITANDO, sit.VIROU_NORMA, sit.NAO_AVANCOU, sit.ENCERRADO))}
</dl></details>
{AVISO_VOTO}
<script>
function abrir(){{var d=location.hash&&document.getElementById(location.hash.slice(1));if(d&&d.tagName==="DETAILS"){{d.open=true;d.scrollIntoView();}}}}
addEventListener("hashchange",abrir);abrir();
</script>"""
    return pagina(f"{v['nome']} — Radar Cáceres",
                  f"Propostas de {v['nome']} na Câmara de Cáceres-MT, com dados oficiais.", corpo, "../", coleta)


def gerar_sobre(coleta):
    tipos = "".join(f"<dt>{esc(t)}</dt><dd>{esc(e)}</dd>" for t, e in EXPLICA_TIPO.items())
    regra = "".join(f"<dt>{esc(g)}</dt><dd>{esc(e)}</dd>" for g, e in REGRA_EXPLICADA)
    corpo = f"""<h1>Como funciona</h1>
<p>O Radar Cáceres mostra o que está registrado no sistema oficial da Câmara Municipal,
o <a href="{SAPL}">SAPL</a>. Não damos nota nem opinião: só organizamos o dado e
colocamos o link para a fonte.</p>
<h2>Como contamos as propostas</h2>
<ul>
<li>Contamos as propostas apresentadas em {" e ".join(ANOS)} em que o vereador aparece como autor.</li>
<li>Quando vários vereadores assinam a mesma proposta, ela conta para cada um deles. Na página de cada vereador
separamos o que ele apresentou como autor principal e o que assinou junto.</li>
<li>Quantidade não é qualidade. Uma lei pode valer mais do que cem pedidos, e o contrário também.</li>
</ul>
<h2 id="regra">Como separamos as propostas</h2>
<p>A Câmara tem muitos tipos de documento. Para facilitar, separamos tudo em cinco grupos.
A regra olha o tipo oficial da proposta e algumas palavras do resumo, e é a mesma para todos os vereadores:</p>
<dl class="glossario">{regra}</dl>
<p>Uma regra automática pode errar em casos raros. Se achar uma proposta no grupo errado,
<a href="https://github.com/eltoncesar/radar-caceres/issues">avise</a>.</p>
<h2>O que cada tipo de proposta quer dizer</h2>
<dl class="glossario">{tipos}</dl>
<h2>O que não mostramos, e por quê</h2>
<ul>
<li><b>Voto de cada vereador:</b> a Câmara não registra no sistema desde agosto de 2020.</li>
<li><b>Presença:</b> as licenças dos vereadores não aparecem no sistema, então uma licença
pareceria falta. Só vamos mostrar depois de conferir.</li>
<li><b>Contatos pessoais:</b> mostramos só o e-mail institucional e o telefone do gabinete.</li>
</ul>
<h2>Achou um erro?</h2>
<p><a href="https://github.com/eltoncesar/radar-caceres/issues">Avise aqui</a>. Corrigimos rápido.</p>
<p>O código e os dados estão abertos em <a href="https://github.com/eltoncesar/radar-caceres">github.com/eltoncesar/radar-caceres</a>.</p>"""
    return pagina("Como funciona — Radar Cáceres", "Como o Radar Cáceres conta os dados.", corpo, "", coleta)


# (os dados da busca agora saem de pagina_inicial.dados_json)


EXEMPLOS_LUGAR = ["Vila Real", "Vila Irene", "Jardim Guanabara", "Cavalhada", "Nova Cáceres",
                  "Junco", "Avenida Sete de Setembro"]


def gerar_busca():
    """A busca mudou para a página inicial; este endereço antigo só redireciona."""
    return """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Radar Cáceres</title>
<script>location.replace("index.html"+(location.hash?"#q="+location.hash.slice(1):"#busca"));</script>
<meta http-equiv="refresh" content="0; url=index.html#busca"></head>
<body><p><a href="index.html#busca">A busca por bairro está na página inicial.</a></p></body></html>"""


ESTILO = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "estilo.css"), encoding="utf-8").read()


def main():
    pagina_inicial.EXPLICA_TIPO.update(EXPLICA_TIPO)
    vereadores = montar_dados()
    with open(os.path.join(BRUTOS, "_coleta.json"), encoding="utf-8") as f:
        coleta = data_br(json.load(f)["data"])
    if os.path.exists(SAIDA):
        shutil.rmtree(SAIDA)
    os.makedirs(os.path.join(SAIDA, "vereador"))
    escrever = lambda caminho, texto: open(os.path.join(SAIDA, caminho), "w", encoding="utf-8").write(texto)
    shutil.copytree(FOTOS, os.path.join(SAIDA, "fotos"))
    escrever("estilo.css", ESTILO)
    escrever("index.html", gerar_index(vereadores, coleta))
    escrever("sobre.html", gerar_sobre(coleta))
    escrever("busca.html", gerar_busca())
    with open(os.path.join(SAIDA, "dados.json"), "w", encoding="utf-8") as f:
        json.dump(pagina_v2.dados(vereadores, coleta, pagina_inicial.dados_json), f, ensure_ascii=False, separators=(",", ":"))
    for v in vereadores:
        escrever(f"vereador/{v['slug']}.html", gerar_vereador(v, coleta))
    print(f"Site gerado em {SAIDA}: {len(vereadores)} vereadores")


if __name__ == "__main__":
    main()
