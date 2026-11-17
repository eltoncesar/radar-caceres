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
<title>{titulo}</title>
<meta name="description" content="{descricao}">
<meta name="theme-color" content="#0b5d4b">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{base}estilo.css">
</head>
<body>
<a class="pular" href="#conteudo">Pular para o conteúdo</a>
<header class="topo"><a href="{base}index.html" class="marca">{marca}<span>Radar <strong>Cáceres</strong></span></a>
<nav aria-label="Principal"><a href="{base}index.html#busca">Bairros</a><a href="{base}index.html#vereadores">Vereadores</a><a href="{base}sobre.html">Como funciona</a></nav></header>
<main id="conteudo">
"""

RODAPE = """</main>
<footer>
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
        f'<li><a href="#{g}"><b>{len(por_grupo[g])}</b><span>{esc(GRUPOS[g][0])}</span></a></li>' for g in grupos)
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


ESTILO = """:root{
--tinta:#0f172a;--texto:#1e293b;--fraco:#5b6577;--linha:#e2e8f0;--fundo:#fff;--suave:#f4f6f8;
--marca:#0b5d4b;--marca-claro:#e6f2ee;--link:#0a58ca;--escuro:#0f172a;
--melhoria:#1d4ed8;--melhoria-f:#e8efff;--cobranca:#a54a00;--cobranca-f:#fff1e3;
--homenagem:#b4235f;--homenagem-f:#fde9f1;--lei:#047857;--lei-f:#e3f6ee;--outros:#5b6577;--outros-f:#eef1f4;
--raio:16px;--sombra:0 1px 2px rgba(15,23,42,.06),0 4px 16px rgba(15,23,42,.05)}
*{box-sizing:border-box}
html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{margin:0;background:var(--fundo);color:var(--texto);font:17px/1.55 Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--link)}
img{max-width:100%}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
.pular{position:absolute;left:-999px;top:8px;background:var(--escuro);color:#fff;padding:8px 12px;border-radius:8px;z-index:9}
.pular:focus{left:8px}
:focus-visible{outline:3px solid var(--link);outline-offset:2px;border-radius:4px}
main,footer,.topo{max-width:1040px;margin:0 auto;padding:0 16px}
.topo{display:flex;flex-wrap:wrap;gap:6px 18px;align-items:center;justify-content:space-between;padding-top:14px;padding-bottom:14px}
.marca{display:flex;align-items:center;gap:8px;color:var(--tinta);text-decoration:none;font-size:1.2rem;letter-spacing:-.01em}
.marca strong{color:var(--marca);font-weight:800}
.marca span{font-weight:700}
.icone-radar{width:30px;height:30px;color:var(--marca)}
.topo nav{display:flex;gap:16px;font-weight:600;font-size:.95rem}
.topo nav a{color:var(--texto);text-decoration:none}
.topo nav a:hover{color:var(--marca)}
h1,h2,h3{color:var(--tinta);letter-spacing:-.02em;line-height:1.15}
h1{font-size:1.9rem;margin:20px 0 8px}
h2{font-size:1.75rem;margin:4px 0 8px}
h3{font-size:.8rem;text-transform:uppercase;letter-spacing:.08em;color:var(--fraco);margin:24px 0 10px}
.sub{color:var(--fraco);font-size:.95rem;margin:4px 0}
.lead{font-size:1.1rem;color:var(--texto);max-width:40em}
.sobretitulo{font-size:.78rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--marca);margin:0 0 6px}
.secao{padding:40px 0 8px}
/* Topo da página inicial */
.hero{padding:12px 0 8px}
.selo{display:inline-flex;align-items:center;gap:8px;background:var(--suave);border-radius:999px;padding:6px 12px;font-size:.85rem;font-weight:600;color:var(--texto);margin:8px 0 4px}
.ponto{width:10px;height:10px;border-radius:50%;background:var(--marca);box-shadow:0 0 0 4px var(--marca-claro)}
.tit-hero{font-size:2.3rem;font-weight:800;max-width:16em;margin:14px 0 10px}
.destaque-total{background:var(--escuro);color:#fff;border-radius:var(--raio);padding:18px 20px;margin:20px 0 10px}
.destaque-total b{display:block;font-size:2.6rem;line-height:1;font-weight:800;letter-spacing:-.02em}
.destaque-total span{color:#cbd5e1}
.contadores{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}
.contador{background:var(--suave);border-radius:var(--raio);padding:14px 16px}
.contador b{display:block;font-size:1.9rem;font-weight:800;line-height:1.1;letter-spacing:-.02em}
.contador span{color:var(--fraco);font-size:.92rem}
.contador.g-melhoria b{color:var(--melhoria)}.contador.g-cobranca b{color:var(--cobranca)}
.contador.g-homenagem b{color:var(--homenagem)}.contador.g-lei b{color:var(--lei)}
.nota{color:var(--fraco);font-size:.88rem;margin-top:12px}
/* Busca */
.campo-busca{display:flex;align-items:center;gap:10px;border:2px solid var(--tinta);border-radius:14px;padding:0 14px;margin:16px 0 10px;background:#fff}
.campo-busca svg{color:var(--fraco);flex:none}
.campo-busca input{flex:1;border:0;font:inherit;font-size:1.08rem;padding:14px 0;background:transparent;color:var(--tinta);min-width:0}
.campo-busca input:focus{outline:none}
.campo-busca:focus-within{outline:3px solid var(--link);outline-offset:2px}
.chips{display:flex;gap:8px;overflow-x:auto;padding:2px 2px 8px;scrollbar-width:none}
.chips::-webkit-scrollbar{display:none}
.chip{flex:none;font:inherit;font-size:.9rem;font-weight:600;padding:8px 14px;border:1px solid var(--linha);border-radius:999px;background:#fff;color:var(--tinta);cursor:pointer}
.chip:hover{border-color:var(--marca)}
.painel{border:1px solid var(--linha);border-radius:20px;padding:20px;margin-top:10px;box-shadow:var(--sombra)}
.grande{margin:0}.grande b{font-size:3rem;font-weight:800;color:var(--melhoria);letter-spacing:-.03em;line-height:1}
.sub-grande{margin:4px 0 0;font-size:1.05rem}
.filtro-ativo{font:inherit;font-size:.88rem;font-weight:600;border:0;border-radius:999px;padding:6px 12px;background:var(--marca-claro);color:var(--marca);margin-bottom:10px;cursor:pointer}
.ranking{list-style:none;padding:0;margin:0}
.ranking li{display:grid;grid-template-columns:1fr auto;align-items:center;gap:2px 10px;padding:6px 0}
.ranking .r-nome{display:flex;align-items:center;gap:8px;font-weight:600;min-width:0}
.ranking .r-nome small{color:var(--fraco);font-weight:500}
.ranking .r-nome img,.autor img,.av{width:28px;height:28px;border-radius:50%;object-fit:cover;flex:none;background:var(--suave)}
.ranking b{font-size:1.05rem}
.ranking i{grid-column:1/-1;display:block;height:6px;border-radius:6px;background:linear-gradient(90deg,var(--melhoria) var(--w),var(--suave) var(--w))}
.ranking .link{font-weight:600}
.props{list-style:none;padding:0;margin:0;display:grid;gap:10px}
.prop{border:1px solid var(--linha);border-left:4px solid var(--outros);border-radius:14px;padding:14px 16px}
.prop.g-melhoria{border-left-color:var(--melhoria)}.prop.g-cobranca{border-left-color:var(--cobranca)}
.prop.g-homenagem{border-left-color:var(--homenagem)}.prop.g-lei{border-left-color:var(--lei)}
.ementa{margin:0 0 8px;font-weight:600;color:var(--tinta);display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;cursor:pointer;overflow-wrap:anywhere}
.ementa.aberta{-webkit-line-clamp:unset;display:block}
.meta{display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center;color:var(--fraco);font-size:.85rem;margin:0 0 8px}
.tag{display:inline-block;font-size:.78rem;font-weight:700;padding:3px 9px;border-radius:999px;background:var(--suave);color:var(--texto)}
.tag.g-melhoria{background:var(--melhoria-f);color:var(--melhoria)}.tag.g-cobranca{background:var(--cobranca-f);color:var(--cobranca)}
.tag.g-homenagem{background:var(--homenagem-f);color:var(--homenagem)}.tag.g-lei{background:var(--lei-f);color:var(--lei)}
.tag.g-outros{background:var(--outros-f);color:var(--outros)}
.autores{display:flex;flex-wrap:wrap;gap:6px 14px;margin-bottom:6px}
.autor{display:inline-flex;align-items:center;gap:6px;color:var(--tinta);font-weight:600;font-size:.88rem;text-decoration:none}
.mais-aut{color:var(--fraco);font-size:.85rem}
.link{font:inherit;font-weight:700;font-size:.92rem;color:var(--link);background:none;border:0;padding:0;cursor:pointer;text-decoration:none}
.link:hover{text-decoration:underline}
.botao{display:block;width:100%;font:inherit;font-weight:700;border:0;border-radius:14px;padding:14px;margin-top:14px;background:var(--escuro);color:#fff;cursor:pointer}
.vazio{font-size:1.05rem}
/* Problema que não some */
.reps{list-style:none;padding:0;margin:16px 0 0;display:grid;gap:10px}
.rep{display:grid;grid-template-columns:auto 1fr;gap:14px;border:1px solid var(--linha);border-radius:var(--raio);padding:14px 16px}
.rep.oculto{display:none}
.vezes{background:var(--escuro);color:#fff;border-radius:12px;padding:8px 10px;text-align:center;min-width:64px;align-self:start}
.vezes b{display:block;font-size:1.7rem;line-height:1;font-weight:800}
.vezes span{font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;color:#cbd5e1}
.rua{margin:0;font-weight:700;color:var(--tinta);font-size:1.05rem}
.bairro{display:block;color:var(--fraco);font-size:.9rem;margin-bottom:6px}
.rep .meta{margin:8px 0 6px}
.aviso-curto{color:var(--fraco);font-size:.9rem;margin-top:12px}
/* Grupos */
.grupos{list-style:none;padding:0;margin:16px 0 0;display:grid;gap:10px}
.grupo{border-radius:var(--raio);padding:16px 18px;background:var(--suave)}
.grupo b{font-size:2rem;font-weight:800;line-height:1;letter-spacing:-.02em}
.grupo .nome-grupo{font-weight:700;color:var(--tinta);margin:6px 0 2px}
.grupo.g-melhoria{background:var(--melhoria-f)}.grupo.g-melhoria b{color:var(--melhoria)}
.grupo.g-cobranca{background:var(--cobranca-f)}.grupo.g-cobranca b{color:var(--cobranca)}
.grupo.g-homenagem{background:var(--homenagem-f)}.grupo.g-homenagem b{color:var(--homenagem)}
.grupo.g-lei{background:var(--lei-f)}.grupo.g-lei b{color:var(--lei)}
.grupo.g-outros b{color:var(--outros)}
/* Crachás */
.filtros{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px;margin:16px 0 6px}
.filtros label{display:flex;flex-direction:column;gap:4px;font-size:.85rem;font-weight:600;color:var(--fraco)}
.filtros label:first-child{grid-column:1/-1}
.filtros input,.filtros select{width:100%;font:inherit;font-size:1rem;color:var(--tinta);padding:10px 12px;border:1px solid #94a3b8;border-radius:10px;background:#fff;min-width:0}
.crachas{list-style:none;padding:0;margin:10px 0 0;display:grid;gap:12px}
.cracha a{display:block;height:100%;border:1px solid var(--linha);border-radius:20px;padding:16px;text-decoration:none;color:inherit;box-shadow:var(--sombra)}
.cracha a:hover{border-color:var(--marca)}
.cab{display:flex;gap:12px;align-items:center}
.cab .foto{width:60px;height:60px}
.nome{font-weight:800;color:var(--tinta);margin:0;font-size:1.05rem}
.total{margin:12px 0 6px;color:var(--fraco)}.total b{font-size:1.5rem;color:var(--tinta)}
.barras{list-style:none;padding:0;margin:0 0 10px}
.barras li{display:grid;grid-template-columns:1fr auto;gap:2px 8px;font-size:.88rem;padding:4px 0}
.barras i{grid-column:1/-1;height:5px;border-radius:5px;background:linear-gradient(90deg,var(--c) var(--w),var(--suave) var(--w))}
.barras .g-melhoria{--c:var(--melhoria)}.barras .g-cobranca{--c:var(--cobranca)}.barras .g-homenagem{--c:var(--homenagem)}.barras .g-lei{--c:var(--lei)}
/* Avisos */
.avisos{display:grid;gap:12px}
.aviso{background:#fff8e6;border-left:4px solid #d39b00;padding:14px 16px;border-radius:10px;margin:16px 0}
.avisos .aviso{margin:0}
.aviso strong{display:block;margin-bottom:4px;color:var(--tinta)}
/* Página do vereador */
.foto{width:64px;height:64px;border-radius:50%;object-fit:cover;flex:none;background:var(--suave)}
.foto.vazia{display:inline-block}
.voltar{margin:8px 0 0;font-weight:600}
.perfil{display:flex;gap:16px;align-items:flex-start;margin-top:8px}
.perfil h1{margin-top:12px}
.perfil .foto{width:96px;height:96px;margin-top:12px}
.destaque{background:var(--escuro);color:#fff;border-radius:var(--raio);padding:16px 18px;margin:18px 0}
.destaque p{margin:0}.destaque b{font-size:2rem;font-weight:800}
.destaque .sub{color:#cbd5e1}
.resumo{list-style:none;padding:0;margin:16px 0 4px;display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px}
.resumo a{display:flex;flex-direction:column;padding:12px 14px;border-radius:14px;text-decoration:none;color:var(--tinta);height:100%;background:var(--suave);font-weight:600}
.resumo b{font-size:1.5rem;line-height:1.1;font-weight:800}
.resumo li:nth-child(1) a{background:var(--melhoria-f)}.resumo li:nth-child(1) b{color:var(--melhoria)}
details{border-top:1px solid var(--linha)}
summary{cursor:pointer;padding:16px 0;font-weight:700;font-size:1.08rem;color:var(--tinta)}
.contagem{color:var(--fraco);font-weight:500}
.explica{color:var(--fraco);margin-top:0}
.propostas{list-style:none;padding:0;margin:0 0 16px}
.propostas li{padding:12px 0;border-bottom:1px solid var(--linha)}
.propostas p{margin:4px 0 0;overflow-wrap:anywhere}
.data{color:var(--fraco);font-size:.88rem;margin-left:8px}
.glossario dt{font-weight:700;margin-top:12px;color:var(--tinta)}.glossario dd{margin:0}
footer{border-top:1px solid var(--linha);margin-top:48px;padding-top:16px;padding-bottom:40px;color:var(--fraco);font-size:.9rem}
@media (min-width:720px){
 .tit-hero{font-size:3rem}
 .contadores{grid-template-columns:repeat(4,1fr)}
 .grupos{grid-template-columns:repeat(3,1fr)}
 .crachas{grid-template-columns:repeat(2,1fr)}
 .filtros{grid-template-columns:minmax(0,2fr) minmax(0,1fr) minmax(0,1fr)}.filtros label:first-child{grid-column:auto}
 .reps{grid-template-columns:repeat(2,1fr)}
}
@media (min-width:1000px){.crachas{grid-template-columns:repeat(3,1fr)}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
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
