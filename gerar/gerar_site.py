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


CABECA = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{titulo}</title>
<meta name="description" content="{descricao}">
<link rel="stylesheet" href="{base}estilo.css">
</head>
<body>
<header class="topo"><a href="{base}index.html" class="marca">Radar Cáceres</a>
<nav><a href="{base}index.html">Vereadores</a><a href="{base}sobre.html">Como funciona</a></nav></header>
<main>
"""

RODAPE = """</main>
<footer>
<p>Dados oficiais do <a href="{sapl}">SAPL da Câmara Municipal de Cáceres</a>, coletados em {coleta}.</p>
<p>Viu um erro? <a href="https://github.com/eltoncesar/radar-caceres/issues">Avise aqui</a> e a gente corrige.</p>
</footer>
</body>
</html>
"""


def pagina(titulo, descricao, corpo, base, coleta):
    return (CABECA.format(titulo=esc(titulo), descricao=esc(descricao), base=base)
            + corpo + RODAPE.format(sapl=SAPL, coleta=coleta))


def foto(v, base):
    if v["foto"]:
        return f'<img class="foto" src="{base}fotos/{v["id"]}.jpg" alt="" width="88" height="88">'
    return '<span class="foto vazia" aria-hidden="true"></span>'


def periodo(v):
    if v["titular"]:
        return "Titular"
    return f'Suplente em exercício de {data_br(v["inicio"])} a {data_br(v["fim"])}'


AVISO_VOTO = """<aside class="aviso"><strong>Por que não mostramos como cada vereador votou?</strong>
A Câmara não registra no sistema oficial o voto de cada vereador desde agosto de 2020.
Hoje só aparece o resultado geral, por exemplo “aprovado por unanimidade”.</aside>
"""

AVISO_PRESENCA = """<aside class="aviso"><strong>E a presença nas sessões?</strong>
Ainda não mostramos. Os registros oficiais de presença têm falhas, como licenças que não aparecem.
Só vamos publicar quando pudermos conferir cada número.</aside>
"""


def gerar_index(vereadores, coleta):
    def cartao(v):
        total = len(v["propostas"])
        cont = collections.Counter(p["grupo"] for p in v["propostas"])
        partes = " · ".join(f"{cont[g]} {GRUPOS[g][0].lower()}" for g in ORDEM_GRUPOS[:4] if cont[g])
        return (f'<li><a class="cartao" href="vereador/{v["slug"]}.html">{foto(v, "")}'
                f'<span class="info"><span class="nome">{esc(v["nome"])}</span>'
                f'<span class="sub">{esc(v["partido"])}{" · " if v["partido"] else ""}{esc(periodo(v))}</span>'
                f'<span class="num"><b>{total}</b> propostas</span>'
                f'<span class="sub">{esc(partes)}</span></span></a></li>')

    titulares = [v for v in vereadores if v["titular"]]
    suplentes = [v for v in vereadores if not v["titular"]]
    corpo = f"""<h1>O que fazem os vereadores de Cáceres</h1>
<p class="lead">Propostas apresentadas na Câmara em {" e ".join(ANOS)}, por vereador.
Toque no nome para ver cada proposta, com link para o documento oficial.</p>
<h2>Vereadores titulares</h2>
<ul class="lista">{"".join(cartao(v) for v in titulares)}</ul>
<h2>Suplentes que assumiram uma vaga</h2>
<p>Ocupam a cadeira quando um titular se afasta.</p>
<ul class="lista">{"".join(cartao(v) for v in suplentes)}</ul>
<p class="nota">O número soma todas as propostas em que o vereador aparece como autor,
inclusive as assinadas junto com outros. As propostas são separadas em pedidos de melhoria,
perguntas e cobranças, homenagens e projetos de lei, com a mesma regra para todos.
<a href="sobre.html">Veja como separamos</a>.</p>
{AVISO_VOTO}{AVISO_PRESENCA}"""
    return pagina("Radar Cáceres — o que fazem os vereadores",
                  "Propostas de cada vereador de Cáceres-MT, com dados oficiais da Câmara.", corpo, "", coleta)


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

    corpo = f"""<p class="voltar"><a href="../index.html">← Todos os vereadores</a></p>
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


ESTILO = """:root{--texto:#1a1a1a;--fraco:#5c5c5c;--linha:#e3e3e3;--fundo:#fff;--suave:#f5f5f5;--link:#0b57d0;--aviso:#fff7e0;--aviso-borda:#e0b400}
*{box-sizing:border-box}
body{margin:0;background:var(--fundo);color:var(--texto);font:17px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--link)}
main,footer,.topo{max-width:760px;margin:0 auto;padding:0 16px}
.topo{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;justify-content:space-between;padding-top:12px;padding-bottom:12px;border-bottom:1px solid var(--linha)}
.marca{font-weight:800;font-size:1.15rem;color:var(--texto);text-decoration:none}
.topo nav{display:flex;gap:16px}
h1{font-size:1.6rem;line-height:1.2;margin:20px 0 8px}
h2{font-size:1.2rem;margin:28px 0 8px}
.lead{font-size:1.05rem;color:var(--fraco)}
.lista{list-style:none;padding:0;margin:0;display:grid;gap:8px}
.cartao{display:flex;gap:12px;align-items:flex-start;padding:12px;border:1px solid var(--linha);border-radius:12px;text-decoration:none;color:inherit;min-height:64px}
.cartao:hover,.cartao:focus{border-color:var(--link)}
.foto{width:64px;height:64px;border-radius:50%;object-fit:cover;flex:none;background:var(--suave)}
.foto.vazia{display:inline-block}
.info{display:flex;flex-direction:column;min-width:0}
.nome{font-weight:700}
.sub{color:var(--fraco);font-size:.92rem;margin:2px 0}
.num{margin-top:2px}
.nota{color:var(--fraco);font-size:.92rem;margin-top:16px}
.aviso{background:var(--aviso);border-left:4px solid var(--aviso-borda);padding:12px 14px;margin:20px 0;border-radius:6px}
.aviso strong{display:block;margin-bottom:4px}
.voltar{margin:16px 0 0}
.perfil{display:flex;gap:16px;align-items:flex-start}
.perfil h1{margin-top:12px}
.perfil .foto{width:88px;height:88px;margin-top:12px}
.destaque{background:var(--suave);border-radius:12px;padding:12px 16px;margin:16px 0}
.destaque p{margin:0}.destaque b{font-size:1.6rem}
.resumo{list-style:none;padding:0;margin:16px 0 4px;display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:8px}
.resumo a{display:flex;flex-direction:column;padding:10px 12px;border:1px solid var(--linha);border-radius:12px;text-decoration:none;color:var(--texto);height:100%}
.resumo b{font-size:1.4rem;line-height:1.1}.resumo span{font-size:.92rem}
details{border-top:1px solid var(--linha)}
summary{cursor:pointer;padding:14px 0;font-weight:700;font-size:1.05rem}
.contagem{color:var(--fraco);font-weight:400}
.explica{color:var(--fraco);margin-top:0}
.propostas{list-style:none;padding:0;margin:0 0 16px}
.propostas li{padding:10px 0;border-bottom:1px solid var(--linha)}
.propostas p{margin:4px 0 0;overflow-wrap:anywhere}
.data{color:var(--fraco);font-size:.88rem;margin-left:8px}
.glossario dt{font-weight:700;margin-top:12px}.glossario dd{margin:0}
footer{border-top:1px solid var(--linha);margin-top:32px;padding-top:12px;padding-bottom:32px;color:var(--fraco);font-size:.9rem}
"""


def main():
    vereadores = montar_dados()
    coleta = data_br(datetime.date.fromtimestamp(os.path.getmtime(os.path.join(BRUTOS, "autorias.json"))).isoformat())
    if os.path.exists(SAIDA):
        shutil.rmtree(SAIDA)
    os.makedirs(os.path.join(SAIDA, "vereador"))
    escrever = lambda caminho, texto: open(os.path.join(SAIDA, caminho), "w", encoding="utf-8").write(texto)
    shutil.copytree(FOTOS, os.path.join(SAIDA, "fotos"))
    escrever("estilo.css", ESTILO)
    escrever("index.html", gerar_index(vereadores, coleta))
    escrever("sobre.html", gerar_sobre(coleta))
    for v in vereadores:
        escrever(f"vereador/{v['slug']}.html", gerar_vereador(v, coleta))
    print(f"Site gerado em {SAIDA}: {len(vereadores)} vereadores")


if __name__ == "__main__":
    main()
