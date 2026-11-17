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
from classificar import GRUPOS, ORDEM as ORDEM_GRUPOS, REGRA_EXPLICADA, classificar  # noqa: E402
import pagina_inicial  # noqa: E402

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
        })

    # Cargo na Mesa Diretora mais recente (a de maior id é a do ano corrente).
    cargos_mesa = {c["id"]: c["descricao"] for c in carregar("cargos_mesa")}
    mesa_atual = max(m["id"] for m in carregar("mesas"))
    cargo = {c["parlamentar"]: cargos_mesa[c["cargo"]] for c in carregar("composicao_mesa") if c["mesa_diretora"] == mesa_atual}

    vereadores = []
    for mand in carregar("mandatos"):
        p = parlamentares[mand["parlamentar"]]
        email = (p.get("email") or "").strip()
        lista = sorted(propostas[p["id"]], key=lambda x: (x["data"] or "", x["id"]), reverse=True)
        vereadores.append({
            "id": p["id"],
            "nome": p["nome_parlamentar"],
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
        })
    vereadores.sort(key=lambda v: (not v["titular"], v["nome"]))
    return vereadores


MARCA = ('<svg class="icone-radar" viewBox="0 0 32 32" aria-hidden="true">'
         '<circle cx="16" cy="16" r="3.2" fill="currentColor"/>'
         '<path d="M10.3 21.7a8 8 0 0 1 0-11.4M21.7 10.3a8 8 0 0 1 0 11.4" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>'
         '<path d="M6.1 25.9a14 14 0 0 1 0-19.8M25.9 6.1a14 14 0 0 1 0 19.8" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" opacity=".55"/>'
         '</svg>')

CABECA = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>document.documentElement.className="js"</script>
<title>{titulo}</title>
<meta name="description" content="{descricao}">
<meta name="theme-color" content="#ffffff">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Roboto+Flex:opsz,wght@8..144,400..800&display=swap" rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400,0..1,0&icon_names=add_road,arrow_back,arrow_forward,celebration,check,cleaning_services,construction,contact_support,directions_bus,expand_more,flood,forest,gavel,landscape,lightbulb,local_hospital,location_on,more_horiz,open_in_new,park,school,search,traffic,water_drop&display=block" rel="stylesheet">
<link rel="stylesheet" href="{base}estilo.css">
</head>
<body>
<nav class="atalhos" aria-label="Atalhos de acessibilidade"><a href="#conteudo" accesskey="1">Ir para o conteúdo <kbd>Alt+1</kbd></a><a href="#menu" accesskey="2">Ir para o menu <kbd>Alt+2</kbd></a><a href="{base}index.html#busca" accesskey="3">Ir para a busca <kbd>Alt+3</kbd></a><a href="#rodape" accesskey="4">Ir para o rodapé <kbd>Alt+4</kbd></a></nav>
<header class="topo"><a href="{base}index.html" class="marca">{marca}<span>Radar <strong>Cáceres</strong></span></a>
<nav id="menu" aria-label="Principal"><a href="{base}index.html#busca">Bairros</a><a href="{base}index.html#vereadores">Vereadores</a><a href="{base}sobre.html">Como funciona</a></nav></header>
<main id="conteudo">
"""

RODAPE = """</main>
<footer id="rodape">
<p><b>Radar Cáceres</b> · feito só com dados oficiais do <a href="{sapl}">SAPL da Câmara Municipal de Cáceres-MT</a>.
Última conferência: {coleta}.</p>
<p>Viu um erro? <a href="https://github.com/eltoncesar/radar-caceres/issues">Avise aqui</a> e a gente corrige.
O código e os dados são abertos.</p>
</footer>
</body>
</html>
"""


def pagina(titulo, descricao, corpo, base, coleta):
    return (CABECA.format(titulo=esc(titulo), descricao=esc(descricao), base=base, marca=MARCA)
            + corpo + RODAPE.format(sapl=SAPL, coleta=coleta))


def foto(v, base):
    if v["foto"]:
        return f'<img class="foto" src="{base}fotos/{v["id"]}.jpg" alt="" width="88" height="88" loading="lazy">'
    return '<span class="foto vazia" aria-hidden="true"></span>'


def periodo(v):
    if v["titular"]:
        return "Titular"
    # As datas de mandato dos suplentes no SAPL não batem com as Portarias da Câmara
    # (ver CONFERENCIA.md). Até cruzarmos as Portarias, não mostramos o período.
    return "Suplente que assumiu uma vaga"


AVISO_VOTO = """<aside class="aviso"><strong>Por que não mostramos como cada vereador votou?</strong>
A Câmara não registra no sistema oficial o voto de cada vereador desde agosto de 2020.
Hoje só aparece o resultado geral, por exemplo “aprovado por unanimidade”.</aside>
"""

AVISO_PRESENCA = """<aside class="aviso"><strong>E a presença nas sessões?</strong>
Ainda não mostramos. Os registros oficiais de presença têm falhas, como licenças que não aparecem.
Só vamos publicar quando pudermos conferir cada número.</aside>
"""


def gerar_index(vereadores, coleta):
    corpo = pagina_inicial.gerar(vereadores, coleta, esc, foto, periodo, SAPL, ANOS, EXEMPLOS_LUGAR)
    return pagina("Radar Cáceres — o que fazem os vereadores de Cáceres-MT",
                  "O que cada vereador de Cáceres-MT propôs, pedido por pedido, com dados oficiais da Câmara.",
                  corpo, "", coleta)


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
            f'<p>{esc(p["ementa"]) or "<em>Sem resumo no sistema oficial.</em>"}</p></li>'
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
<section class="destaque"><p><b>{total}</b> propostas em {" e ".join(ANOS)}</p>
<p class="sub">{principal} como autor principal · {total - principal} assinadas junto com outros vereadores</p></section>
{f'<ul class="resumo">{resumo}</ul><p class="sub">Toque num grupo para ler proposta por proposta.</p>' if grupos else "<p>Nenhuma proposta registrada no período.</p>"}
{"".join(blocos)}
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


EXEMPLOS_LUGAR = ["Cavalhada", "Vila Irene", "Junco", "Espírito Santo", "Nova Cáceres",
                  "Massa Barro", "Jardim das Oliveiras", "Vila Real", "Guanabara", "Caramujo"]


def gerar_busca():
    """A busca mudou para a página inicial; este endereço antigo só redireciona."""
    return """<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Radar Cáceres</title>
<script>location.replace("index.html"+(location.hash?"#q="+location.hash.slice(1):"#busca"));</script>
<meta http-equiv="refresh" content="0; url=index.html#busca"></head>
<body><p><a href="index.html#busca">A busca por bairro está na página inicial.</a></p></body></html>"""


ESTILO = """/* Material Design 3 — esquema gerado com material-color-utilities a partir de #1b6b57.
   Tons de texto escurecidos no mesmo matiz para contraste AAA (>= 7:1). */
:root{
--md-primary:#005342;--md-on-primary:#fff;--md-primary-container:#7ef8d4;--md-on-primary-container:#002018;
--md-secondary:#364d46;--md-secondary-container:#cee9dd;--md-on-secondary-container:#072019;
--md-tertiary-container:#c4e7ff;--md-on-tertiary-container:#001e2c;
--md-error:#ba1a1a;--md-error-container:#ffdad6;--md-on-error-container:#410002;
--md-surface:#fff;--md-on-surface:#191c1b;--md-on-surface-variant:#3f4945;
--md-surface-container-lowest:#fff;--md-surface-container-low:#f2f4f1;--md-surface-container:#eceeeb;
--md-surface-container-high:#e6e9e6;--md-surface-container-highest:#e1e3e0;
--md-outline:#6f7975;--md-outline-variant:#bfc9c3;--md-inverse-surface:#2e312f;--md-inverse-on-surface:#eff1ee;--md-inverse-primary:#60dbb9;
--g-melhoria:#00498c;--g-melhoria-c:#d5e3ff;--g-melhoria-on:#001c3b;
--g-cobranca:#6e3e00;--g-cobranca-c:#ffdcbf;--g-cobranca-on:#2d1600;
--g-homenagem:#970020;--g-homenagem-c:#ffdad9;--g-homenagem-on:#410008;
--g-lei:#00543e;--g-lei-c:#83f8ce;--g-lei-on:#002117;
--g-outros:#364d46;--g-outros-c:#cee9dd;--g-outros-on:#072019;
--md-destaque:#97001a;--md-destaque-c:#ffdad8;
--shape-xs:4px;--shape-s:8px;--shape-m:12px;--shape-l:16px;--shape-xl:28px;--shape-full:999px;
--elev-1:0 1px 2px rgba(0,0,0,.3),0 1px 3px 1px rgba(0,0,0,.15);
--elev-2:0 1px 2px rgba(0,0,0,.3),0 2px 6px 2px rgba(0,0,0,.15);
--fonte:"Roboto Flex",Roboto,system-ui,-apple-system,"Segoe UI",sans-serif;
--ease:cubic-bezier(.2,0,0,1)}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;accent-color:var(--md-primary);caret-color:var(--md-primary)}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}
body{margin:0;background:var(--md-surface);color:var(--md-on-surface);font:400 1rem/1.5rem var(--fonte);letter-spacing:.01em}
::selection{background:var(--md-primary-container);color:var(--md-on-primary-container)}
a{color:var(--md-primary);text-underline-offset:.2em;text-decoration-thickness:.07em}
img{max-width:100%}
b{font-weight:700}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.ms{font-family:"Material Symbols Rounded";font-weight:400;font-style:normal;font-size:1.25rem;line-height:1;display:inline-block;
 letter-spacing:normal;text-transform:none;white-space:nowrap;direction:ltr;-webkit-font-feature-settings:"liga";font-feature-settings:"liga";
 font-variation-settings:"FILL" 0,"wght" 400,"GRAD" 0,"opsz" 24;vertical-align:-.22em;flex:none}
.atalhos{position:absolute;left:8px;top:8px;z-index:9;display:flex;flex-wrap:wrap;gap:8px}
.atalhos a{position:absolute;left:-9999px;background:var(--md-inverse-surface);color:var(--md-inverse-on-surface);padding:10px 16px;border-radius:var(--shape-s);font-weight:500;text-decoration:none}
.atalhos a:focus{position:static}
.atalhos kbd{font:inherit;opacity:.8;margin-left:6px}
:focus-visible{outline:3px solid var(--md-primary);outline-offset:2px;border-radius:var(--shape-xs)}
main,footer{max-width:1040px;margin:0 auto;padding:0 16px}
/* Tipografia M3 */
h1,h2,h3{font-family:var(--fonte);color:var(--md-on-surface);margin:0}
h1{font-size:2rem;line-height:2.5rem;font-weight:500;margin:20px 0 8px}
h2{font-size:1.75rem;line-height:2.25rem;font-weight:500;letter-spacing:0;margin:0 0 8px}
h3{font-size:.875rem;line-height:1.25rem;font-weight:500;letter-spacing:.006em;color:var(--md-on-surface-variant);margin:24px 0 8px}
.sub{color:var(--md-on-surface-variant);font-size:1rem;line-height:1.5rem;margin:4px 0}
.lead{font-size:1.125rem;line-height:1.75rem;color:var(--md-on-surface-variant);max-width:38em;margin:0 0 8px}
.nota{color:var(--md-on-surface-variant);font-size:.875rem;line-height:1.25rem;margin-top:12px}
/* Top app bar */
.topo{position:relative;z-index:5;background:var(--md-surface);display:flex;flex-wrap:wrap;gap:4px 16px;align-items:center;justify-content:space-between;
 max-width:none;padding:8px max(16px,calc((100% - 1040px)/2 + 16px));border-bottom:1px solid var(--md-outline-variant)}
.marca{display:flex;align-items:center;gap:10px;color:var(--md-on-surface);text-decoration:none;font-size:1.375rem;line-height:1.75rem;font-weight:500;min-height:48px}
.marca strong{color:var(--md-primary);font-weight:700}
.icone-radar{width:28px;height:28px;color:var(--md-primary)}
.topo nav{display:flex;gap:4px;margin:0 -12px}
.topo nav a{position:relative;display:inline-flex;align-items:center;min-height:40px;padding:0 12px;border-radius:var(--shape-full);
 color:var(--md-primary);font-size:.875rem;font-weight:500;letter-spacing:.006em;text-decoration:none;overflow:hidden}
/* Camada de estado M3 (hover 8%, foco/pressão 10%) */
.topo nav a::after,.chip::after,.aba::after,.botao::after,.link::after,.barras a::after,.resumo a::after,.ficha::after,summary::after{
 content:"";position:absolute;inset:0;border-radius:inherit;background:currentColor;opacity:0;transition:opacity .2s var(--ease);pointer-events:none}
.topo nav a:hover::after,.chip:hover::after,.aba:hover::after,.botao:hover::after,.link:hover::after,.barras a:hover::after,.resumo a:hover::after,.ficha:hover::after,summary:hover::after{opacity:.08}
.topo nav a:active::after,.chip:active::after,.aba:active::after,.botao:active::after,.link:active::after,.barras a:active::after,.resumo a:active::after,.ficha:active::after{opacity:.12}
.secao{padding:40px 0 8px}
/* Topo da página inicial */
.hero{padding:16px 0 8px}
.selo{display:inline-flex;align-items:center;gap:6px;min-height:32px;padding:0 12px;border-radius:var(--shape-s);background:var(--md-secondary-container);
 color:var(--md-on-secondary-container);font-size:.875rem;font-weight:500;margin:8px 0 12px}
.tit-hero{font-size:2.25rem;line-height:2.75rem;font-weight:500;letter-spacing:-.01em;margin:4px 0 12px;max-width:15em}
.tit-hero em{font-style:normal;color:var(--md-primary)}
.radar-total{display:flex;align-items:center;gap:20px;background:var(--md-primary);color:var(--md-on-primary);border-radius:var(--shape-xl);padding:24px;margin:24px 0 12px}
.radar{position:relative;flex:none;width:92px;height:92px;border-radius:50%;background:rgba(255,255,255,.08)}
.anel{position:absolute;inset:0;margin:auto;border-radius:50%;border:1px solid rgba(255,255,255,.4)}
.a1{width:32%;height:32%}.a2{width:64%;height:64%}.a3{width:100%;height:100%}
.feixe{position:absolute;inset:0;border-radius:50%;background:conic-gradient(from 0deg,transparent 0deg,rgba(126,248,212,.55) 50deg,transparent 52deg);animation:varre 4s linear infinite}
@keyframes varre{to{transform:rotate(360deg)}}
.eco{position:absolute;width:8px;height:8px;border-radius:50%;background:var(--md-primary-container)}
.e1{left:62%;top:24%}.e2{left:28%;top:62%}
.radar-num b{display:block;font-size:3.5625rem;line-height:4rem;font-weight:500;letter-spacing:-.016em;font-variant-numeric:tabular-nums}
.radar-num span{display:block;font-size:1rem;line-height:1.5rem;opacity:.92}
.contadores{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.contador{border-radius:var(--shape-l);padding:16px;background:var(--md-surface-container-low)}
.contador b{display:block;font-size:2rem;line-height:2.5rem;font-weight:500;font-variant-numeric:tabular-nums}
.contador span{display:block;color:var(--md-on-surface-variant);font-size:.875rem;line-height:1.25rem}
.contador.g-melhoria{background:var(--g-melhoria-c)}.contador.g-melhoria b{color:var(--g-melhoria)}
.contador.g-cobranca{background:var(--g-cobranca-c)}.contador.g-cobranca b{color:var(--g-cobranca)}
.contador.g-homenagem{background:var(--g-homenagem-c)}.contador.g-homenagem b{color:var(--g-homenagem)}
.contador.g-lei{background:var(--g-lei-c)}.contador.g-lei b{color:var(--g-lei)}
.contador span{color:var(--md-on-surface)}
/* Barra de busca M3 */
.campo-busca{display:flex;align-items:center;gap:12px;min-height:56px;padding:0 16px;margin:16px 0 12px;border-radius:var(--shape-xl);
 background:var(--md-surface-container-high);color:var(--md-on-surface-variant)}
.campo-busca:focus-within{outline:2px solid var(--md-primary);outline-offset:0}
.campo-busca .ms{font-size:1.5rem}
.campo-busca input{flex:1;min-width:0;border:0;background:transparent;font:400 1rem/1.5rem var(--fonte);color:var(--md-on-surface);padding:16px 0}
.campo-busca input::placeholder{color:var(--md-on-surface-variant)}
.campo-busca input:focus{outline:none}
/* Chips M3 (sugestão e filtro) */
.chips,.abas{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;padding:2px 2px 6px;margin:0 -2px}
.chips::-webkit-scrollbar,.abas::-webkit-scrollbar{display:none}
.chip,.aba{position:relative;flex:none;display:inline-flex;align-items:center;gap:8px;height:32px;padding:0 16px;border-radius:var(--shape-s);
 border:1px solid var(--md-outline);background:transparent;color:var(--md-on-surface-variant);font:500 .875rem/1.25rem var(--fonte);letter-spacing:.006em;cursor:pointer;overflow:hidden}
.chip{padding-left:8px}.chip .ms{font-size:1.125rem;color:var(--md-primary)}
.chip::before,.aba::before{content:"";position:absolute;inset:-8px 0}
.aba[aria-pressed="true"]{background:var(--md-secondary-container);border-color:var(--md-secondary-container);color:var(--md-on-secondary-container);padding-left:8px}
.aba[aria-pressed="true"]::before{content:"check";position:static;font-family:"Material Symbols Rounded";font-size:1.125rem;line-height:1;-webkit-font-feature-settings:"liga";font-feature-settings:"liga"}
.abas{margin-top:4px}
/* Painel de resultados */
.painel{margin-top:20px}
.grande{margin:0}.grande b{font-size:2.8125rem;line-height:3.25rem;font-weight:500;color:var(--md-primary);font-variant-numeric:tabular-nums}
.sub-grande{margin:4px 0 0;font-size:1rem;line-height:1.5rem}
.ranking{list-style:none;padding:0;margin:0;border-radius:var(--shape-l);background:var(--md-surface-container-low);padding:4px 16px}
.ranking li{display:grid;grid-template-columns:1fr auto;align-items:center;gap:6px 12px;padding:10px 0;min-height:56px}
.ranking li+li{border-top:1px solid var(--md-outline-variant)}
.ranking .r-nome{display:flex;align-items:center;gap:12px;font-size:1rem;min-width:0}
.ranking .r-nome small{color:var(--md-on-surface-variant);font-size:.875rem}
.ranking .r-nome img,.autor img,.av{width:32px;height:32px;border-radius:50%;object-fit:cover;flex:none;background:var(--md-surface-container-high)}
.ranking b{font-size:1rem;font-weight:500;font-variant-numeric:tabular-nums}
.ranking i{grid-column:1/-1;display:block;height:4px;border-radius:var(--shape-full);background:linear-gradient(90deg,var(--md-primary) var(--w),var(--md-secondary-container) var(--w))}
.ranking .link{font-size:1rem}
/* Cartões de proposta (outlined card M3) */
.props{list-style:none;padding:0;margin:0;display:grid;gap:12px}
.prop{display:flex;gap:16px;align-items:flex-start;border:1px solid var(--md-outline-variant);border-radius:var(--shape-m);padding:16px;background:var(--md-surface-container-lowest)}
.ic-prop{display:grid;place-items:center;width:40px;height:40px;border-radius:50%;font-size:1.375rem;background:var(--md-secondary-container);color:var(--md-on-secondary-container)}
.ic-prop.g-melhoria{background:var(--g-melhoria-c);color:var(--g-melhoria-on)}.ic-prop.g-cobranca{background:var(--g-cobranca-c);color:var(--g-cobranca-on)}
.ic-prop.g-homenagem{background:var(--g-homenagem-c);color:var(--g-homenagem-on)}.ic-prop.g-lei{background:var(--g-lei-c);color:var(--g-lei-on)}
.prop-corpo{min-width:0;flex:1}
.ementa{margin:0 0 8px;font-size:1rem;line-height:1.5rem;color:var(--md-on-surface);display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;cursor:pointer;overflow-wrap:anywhere}
.ementa.aberta{-webkit-line-clamp:unset;display:block}
.meta{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center;color:var(--md-on-surface-variant);font-size:.875rem;line-height:1.25rem;margin:0 0 8px}
.tag{display:inline-flex;align-items:center;gap:4px;height:24px;padding:0 8px;border-radius:var(--shape-s);background:var(--md-surface-container-high);color:var(--md-on-surface-variant);font-size:.75rem;line-height:1rem;font-weight:500;letter-spacing:.03em}
.tag .ms{font-size:1rem}
.tag.g-melhoria{background:var(--g-melhoria-c);color:var(--g-melhoria-on)}.tag.g-cobranca{background:var(--g-cobranca-c);color:var(--g-cobranca-on)}
.tag.g-homenagem{background:var(--g-homenagem-c);color:var(--g-homenagem-on)}.tag.g-lei{background:var(--g-lei-c);color:var(--g-lei-on)}
.tag.g-outros{background:var(--g-outros-c);color:var(--g-outros-on)}
.autores{display:flex;flex-wrap:wrap;gap:6px 16px;margin-bottom:4px}
.autor{display:inline-flex;align-items:center;gap:8px;min-height:40px;color:var(--md-on-surface);font-weight:500;font-size:.875rem;text-decoration:none}
.autor:hover{text-decoration:underline}
.mais-aut{color:var(--md-on-surface-variant);font-size:.875rem}
/* Botões M3 */
.link{position:relative;display:inline-flex;align-items:center;gap:6px;min-height:40px;padding:0 12px;margin-left:-12px;border:0;border-radius:var(--shape-full);
 background:none;color:var(--md-primary);font:500 .875rem/1.25rem var(--fonte);letter-spacing:.006em;cursor:pointer;text-decoration:none;overflow:hidden}
.link .ms{font-size:1.125rem}
.botao{position:relative;display:flex;align-items:center;justify-content:center;width:100%;min-height:48px;margin-top:16px;border:0;border-radius:var(--shape-full);
 background:var(--md-secondary-container);color:var(--md-on-secondary-container);font:500 .875rem/1.25rem var(--fonte);letter-spacing:.006em;cursor:pointer;overflow:hidden}
.vazio{font-size:1rem;padding:16px;border-radius:var(--shape-m);background:var(--md-surface-container-low)}
/* O problema que não some */
.reps{list-style:none;padding:0;margin:16px 0 0;display:grid;gap:12px}
.rep{display:grid;grid-template-columns:auto 1fr;gap:16px;border-radius:var(--shape-m);padding:16px;background:var(--md-surface-container-low)}
.rep.oculto{display:none}
.vezes{display:grid;place-content:center;text-align:center;min-width:72px;min-height:72px;padding:8px;border-radius:var(--shape-l);background:var(--md-destaque-c);color:var(--md-destaque)}
.vezes b{font-size:1.75rem;line-height:2rem;font-weight:600;font-variant-numeric:tabular-nums}
.vezes span{font-size:.75rem;line-height:1rem;font-weight:500;letter-spacing:.03em;color:#410006}
.rua{margin:0;font-size:1.125rem;line-height:1.5rem;font-weight:500;color:var(--md-on-surface)}
.bairro{display:block;color:var(--md-on-surface-variant);font-size:.875rem;margin-bottom:8px}
.rep .meta{margin:8px 0 0}
.aviso-curto{color:var(--md-on-surface-variant);font-size:.875rem;line-height:1.25rem;margin-top:12px;max-width:62ch}
/* Homenagem ou trabalho (filled cards) */
.grupos{list-style:none;padding:0;margin:16px 0 0;display:grid;gap:12px}
.grupo{position:relative;border-radius:var(--shape-m);padding:16px;background:var(--md-surface-container-low)}
.ic-grupo{font-size:1.5rem;margin-bottom:8px}
.grupo b{display:block;font-size:2rem;line-height:2.5rem;font-weight:500;font-variant-numeric:tabular-nums}
.grupo .nome-grupo{font-size:1.125rem;line-height:1.5rem;font-weight:500;color:var(--md-on-surface);margin:4px 0 2px}
.grupo.g-melhoria{background:var(--g-melhoria-c)}.grupo.g-melhoria b,.grupo.g-melhoria .ic-grupo{color:var(--g-melhoria)}
.grupo.g-cobranca{background:var(--g-cobranca-c)}.grupo.g-cobranca b,.grupo.g-cobranca .ic-grupo{color:var(--g-cobranca)}
.grupo.g-homenagem{background:var(--g-homenagem-c)}.grupo.g-homenagem b,.grupo.g-homenagem .ic-grupo{color:var(--g-homenagem)}
.grupo.g-lei{background:var(--g-lei-c)}.grupo.g-lei b,.grupo.g-lei .ic-grupo{color:var(--g-lei)}
.grupo .sub{color:var(--md-on-surface)}
/* Filtros (outlined text fields) */
.filtros{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:12px;margin:16px 0 8px}
.filtros label{display:flex;flex-direction:column;gap:4px;font-size:.75rem;line-height:1rem;font-weight:500;color:var(--md-on-surface-variant);letter-spacing:.03em}
.filtros label:first-child{grid-column:1/-1}
.filtros input,.filtros select{width:100%;min-height:56px;font:400 1rem/1.5rem var(--fonte);color:var(--md-on-surface);padding:0 16px;border:1px solid var(--md-outline);border-radius:var(--shape-xs);background:var(--md-surface)}
.filtros input:hover,.filtros select:hover{border-color:var(--md-on-surface)}
.filtros input:focus,.filtros select:focus{outline:none;border:2px solid var(--md-primary);padding:0 15px}
/* Crachás (outlined cards) */
.crachas{list-style:none;padding:0;margin:12px 0 0;display:grid;gap:12px}
.cracha{display:flex;flex-direction:column;border:1px solid var(--md-outline-variant);border-radius:var(--shape-m);padding:16px;background:var(--md-surface-container-lowest)}
.cab{display:flex;gap:16px;align-items:flex-start}
.cab .foto{width:64px;height:64px}
.cracha .nome{font-size:1.375rem;line-height:1.75rem;font-weight:500;color:var(--md-on-surface);margin:0}
.cracha .nome a{color:inherit;text-decoration:none}.cracha .nome a:hover{text-decoration:underline}
.cracha .sub{font-size:.875rem;line-height:1.25rem;margin:2px 0 0}
.partido{margin:4px 0 0;font-size:.875rem;font-weight:500}
.cargo{display:inline-flex;align-items:center;height:28px;margin:8px 0 0;padding:0 10px;border-radius:var(--shape-s);background:var(--md-tertiary-container);color:var(--md-on-tertiary-container);font-size:.75rem;font-weight:500;letter-spacing:.03em}
.total{margin:16px 0 4px;color:var(--md-on-surface-variant)}.total b{font-size:1.5rem;line-height:2rem;font-weight:500;color:var(--md-on-surface);font-variant-numeric:tabular-nums}
.rot{margin:8px 0 0;font-size:.75rem;line-height:1rem;font-weight:500;color:var(--md-on-surface-variant);letter-spacing:.03em}
.barras{list-style:none;padding:0;margin:4px 0 8px}
.barras a{position:relative;display:grid;grid-template-columns:1fr auto;gap:6px 8px;align-content:center;min-height:48px;padding:6px 8px;margin:0 -8px;border-radius:var(--shape-s);color:var(--md-on-surface);text-decoration:none;font-size:.875rem;overflow:hidden}
.barras b{font-weight:500;font-variant-numeric:tabular-nums}
.barras b::after{content:"›";margin-left:4px;color:var(--md-on-surface-variant);font-weight:400}
.barras i{grid-column:1/-1;height:4px;border-radius:var(--shape-full);background:linear-gradient(90deg,var(--c) var(--w),var(--md-surface-container-high) var(--w))}
.barras .g-melhoria{--c:var(--g-melhoria)}.barras .g-cobranca{--c:var(--g-cobranca)}.barras .g-homenagem{--c:var(--g-homenagem)}.barras .g-lei{--c:var(--g-lei)}.barras .g-outros{--c:var(--g-outros)}
.ficha{position:relative;display:inline-flex;align-items:center;gap:6px;align-self:flex-start;margin-top:auto;min-height:40px;padding:0 16px;border:1px solid var(--md-outline);border-radius:var(--shape-full);color:var(--md-primary);font-size:.875rem;font-weight:500;text-decoration:none;overflow:hidden}
.ficha .ms{font-size:1.125rem}
/* De onde vêm os números */
.fontes{display:grid;gap:12px;margin:16px 0 0}
.fontes div{border-radius:var(--shape-m);padding:16px;background:var(--md-surface-container-low)}
.fontes dt{font-size:1.125rem;line-height:1.5rem;font-weight:500;color:var(--md-on-surface)}
.fontes dd{margin:6px 0 0;color:var(--md-on-surface-variant);max-width:62ch}
/* Avisos */
.aviso{background:var(--md-surface-container-low);border:1px solid var(--md-outline-variant);border-radius:var(--shape-m);padding:16px;margin:16px 0}
.aviso strong{display:block;margin-bottom:4px;font-weight:500;color:var(--md-on-surface)}
/* Página do vereador */
.foto{width:64px;height:64px;border-radius:50%;object-fit:cover;flex:none;background:var(--md-surface-container-high)}
.foto.vazia{display:inline-block}
.voltar{margin:12px 0 0}
.voltar a{display:inline-flex;align-items:center;min-height:40px;font-weight:500;font-size:.875rem}
.perfil{display:flex;gap:16px;align-items:flex-start;margin-top:8px}
.perfil h1{margin-top:8px}
.perfil .foto{width:96px;height:96px;margin-top:8px}
.destaque{background:var(--md-primary);color:var(--md-on-primary);border-radius:var(--shape-xl);padding:20px 24px;margin:20px 0}
.destaque p{margin:0}.destaque b{font-size:2.25rem;line-height:2.75rem;font-weight:500;font-variant-numeric:tabular-nums}
.destaque .sub{color:var(--md-on-primary);opacity:.92}
.resumo{list-style:none;padding:0;margin:16px 0 8px;display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}
.resumo a{position:relative;display:flex;flex-direction:column;height:100%;padding:16px;border-radius:var(--shape-m);background:var(--md-surface-container-low);color:var(--md-on-surface);text-decoration:none;font-weight:500;overflow:hidden}
.resumo b{font-size:1.75rem;line-height:2.25rem;font-weight:500}
.resumo a.g-melhoria{background:var(--g-melhoria-c)}.resumo a.g-melhoria b{color:var(--g-melhoria)}
.resumo a.g-cobranca{background:var(--g-cobranca-c)}.resumo a.g-cobranca b{color:var(--g-cobranca)}
.resumo a.g-homenagem{background:var(--g-homenagem-c)}.resumo a.g-homenagem b{color:var(--g-homenagem)}
.resumo a.g-lei{background:var(--g-lei-c)}.resumo a.g-lei b{color:var(--g-lei)}
details{border-top:1px solid var(--md-outline-variant)}
summary{position:relative;cursor:pointer;padding:16px 8px;margin:0 -8px;border-radius:var(--shape-s);font-size:1.125rem;line-height:1.5rem;font-weight:500;color:var(--md-on-surface);overflow:hidden}
.contagem{color:var(--md-on-surface-variant);font-weight:400}
.explica{color:var(--md-on-surface-variant);margin-top:0}
.propostas{list-style:none;padding:0;margin:0 0 16px}
.propostas li{padding:12px 0;border-bottom:1px solid var(--md-outline-variant)}
.propostas p{margin:4px 0 0;overflow-wrap:anywhere}
.data{color:var(--md-on-surface-variant);font-size:.875rem;margin-left:8px}
.glossario dt{font-weight:500;margin-top:12px}.glossario dd{margin:0;color:var(--md-on-surface-variant)}
footer{margin-top:48px;padding-top:24px;padding-bottom:40px;border-top:1px solid var(--md-outline-variant);color:var(--md-on-surface-variant);font-size:.875rem;line-height:1.25rem}
/* Entrada suave: só opacidade, a partir de um estado já visível */
@media (prefers-reduced-motion:no-preference){
 .js .entra{opacity:.001;transition:opacity .5s var(--ease)}
 .js .entra.visivel{opacity:1}
}
@media (min-width:720px){
 .topo{position:sticky;top:0}
 h1{font-size:2.8125rem;line-height:3.25rem}
 .tit-hero{font-size:3.5625rem;line-height:4rem}
 .radar{width:128px;height:128px}
 .contadores{grid-template-columns:repeat(4,minmax(0,1fr))}
 .grupos{grid-template-columns:repeat(3,minmax(0,1fr))}
 .crachas,.reps,.fontes{grid-template-columns:repeat(2,minmax(0,1fr))}
 .filtros{grid-template-columns:minmax(0,2fr) minmax(0,1fr) minmax(0,1fr)}.filtros label:first-child{grid-column:auto}
}
@media (min-width:1000px){.crachas{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (prefers-reduced-motion:reduce){.feixe{animation:none}}
"""


def main():
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
    pagina_inicial.escrever_dados(os.path.join(SAIDA, "dados.json"), vereadores, coleta)
    for v in vereadores:
        escrever(f"vereador/{v['slug']}.html", gerar_vereador(v, coleta))
    print(f"Site gerado em {SAIDA}: {len(vereadores)} vereadores")


if __name__ == "__main__":
    main()
