"""Página inicial (versão 2): estrutura da proposta Material Design 3 do usuário,
ligada aos dados reais do SAPL.

Seções: Panorama (total, raio-x e 4 indicadores) · Seu bairro (busca, filtros e
propostas) · O problema que não some (painéis que abrem) · Vereadores (cartões ou
tabela, com dossiê lateral) · De onde vêm os números.

A página funciona sem JavaScript (cartões levam à página de cada vereador). O
JavaScript acrescenta a busca, os filtros, o dossiê lateral e a busca rápida.
"""
import collections
import json

import situacao as sit
from classificar import GRUPOS, ORDEM as ORDEM_GRUPOS
from pagina_inicial import (ICONE_ASSUNTO, ICONE_GRUPO, NOME_ASSUNTO, TIPOS_LEI_DE_FATO, contas_situacao,
                            icone, mes_ano, montar, nome_proprio, texto_presenca, _num)
from resumo import resumo

CURTO = {"melhoria": "Melhorias", "cobranca": "Cobranças", "lei": "Leis", "homenagem": "Homenagens", "outros": "Outros"}
DESCR = {"melhoria": "Pedidos à Prefeitura: obra, conserto, serviço, equipamento.",
         "cobranca": "Pedidos de informação e de explicação ao poder público.",
         "homenagem": "Aplausos, pesar, títulos de cidadão, nomes de rua.",
         "lei": "Propostas que criam ou mudam leis e regras.",
         "outros": "Pedidos internos da Câmara e outros."}
QUATRO = ["melhoria", "cobranca", "homenagem", "lei"]
MIN_REPETE = 3


def pct(parte, todo):
    return f"{100 * parte / todo:.1f}".replace(".", ",") if todo else "0"


def repetidos_com_pedidos(lista, rr, rb):
    grupos = collections.defaultdict(list)
    for p in lista:
        for r in p["r"]:
            for s in p["s"]:
                grupos[(r, s)].append(p)
    saida = []
    for (r, s), ps in grupos.items():
        if len(ps) < MIN_REPETE:
            continue
        ps = sorted(ps, key=lambda p: (p["d"] or "", p["i"]))
        bairro = collections.Counter(b for p in ps for b in p["b"]).most_common(1)
        saida.append({"rua": rr[r], "bairro": rb[bairro[0][0]] if bairro else "", "assunto": s,
                      "pedidos": ps, "autores": {a for p in ps for a in p["a"]}})
    saida.sort(key=lambda x: (-len(x["pedidos"]), -len(x["autores"]), x["rua"]))
    return saida


def perfis(vereadores):
    """Dados do dossiê lateral de cada vereador (lidos pelo JavaScript)."""
    out = {}
    for v in vereadores:
        c = collections.Counter(p["grupo"] for p in v["propostas"])
        resp, ped, viraram, leis = contas_situacao(v["propostas"])
        pr = v["presenca"]
        out[v["id"]] = {
            "nome": v["nome"], "completo": nome_proprio(v["nome_completo"]), "partido": v["partido"],
            "slug": v["slug"], "foto": v["foto"], "titular": v["titular"], "cargo": v["cargo"],
            "grupos": {g: c[g] for g in ORDEM_GRUPOS}, "total": len(v["propostas"]),
            "respondidos": resp, "pedidos": ped, "viraram": viraram, "leis": leis,
            "presenca": {"sessoes": pr["sessoes"], "presente": pr["presente"], "faltas": len(pr["faltas"]),
                         "justificadas": len(pr["justificadas"]),
                         "licencas": [{"inicio": l["inicio"], "fim": l["fim"], "motivo": l["motivo"]} for l in pr["licencas"]]},
            "discursos": len(v["discursos"]),
            "recentes": [p["id"] for p in v["propostas"][:5]],
        }
    return out


def gerar(vereadores, coleta_br, esc, foto, periodo, sapl, anos, exemplos_lugar, data_br):
    lista, rr, rb = montar(vereadores)
    cont = collections.Counter(p["g"] for p in lista)
    pedidos = [p for p in lista if p["tn"] in ("Indicação", "Requerimento")]
    respondidos = sum(p["s"] is not None and p.get("x") == "respondido" for p in pedidos)
    total = len(lista)
    reps = repetidos_com_pedidos(lista, rr, rb)
    por_id = {v["id"]: v for v in vereadores}

    # ---------------- Panorama ----------------
    segmentos = "".join(
        f'<button type="button" class="seg" data-g="{g}" style="flex:{cont[g]}" '
        f'aria-label="{esc(GRUPOS[g][0])}: {_num(cont[g])} propostas ({pct(cont[g], total)}%)"></button>'
        for g in QUATRO + ["outros"] if cont[g])
    kpis = "".join(
        f'<a class="kpi g-{g}" href="#busca" data-g="{g}">'
        f'<span class="kpi-topo"><span class="kpi-ic">{icone(ICONE_GRUPO[g])}</span>'
        f'<span class="kpi-pct">{pct(cont[g], total)}%</span></span>'
        f'<b>{_num(cont[g])}</b><span class="kpi-nome">{esc(GRUPOS[g][0])}</span>'
        f'<span class="kpi-desc">{esc(DESCR[g])}</span></a>' for g in QUATRO)
    panorama = f"""<section id="panorama" class="hero" aria-labelledby="titulo-topo">
<div class="container">
<p class="selo">{icone("verified")}Dados oficiais do SAPL da Câmara de Cáceres-MT</p>
<h1 id="titulo-topo">Homenagem ou trabalho? Veja o que a Câmara de Cáceres faz.</h1>
<p class="lead">Tudo que os vereadores apresentaram em {" e ".join(anos)}, em linguagem direta: os pedidos de melhoria
nos bairros, as cobranças à Prefeitura, as homenagens e os projetos de lei. Cada número leva ao documento oficial.</p>
<div class="bento">
<div class="cartao-total">
<div class="total-linha"><div><b class="total-num" data-conta="{total}">{_num(total)}</b>
<span class="total-rot">propostas apresentadas pelos vereadores até agora</span></div>
<span class="atualizado">{icone("schedule")}Atualizado em {coleta_br}</span></div>
<a class="total-resp" href="#busca" data-x="respondido">{icone("mark_email_read")}<span><b>{_num(respondidos)}</b> de {_num(len(pedidos))} pedidos
já têm resposta escrita da Prefeitura</span>{icone("chevron_right", "seta")}</a>
<div class="raiox"><p class="raiox-leg"><span id="raiox-rot"><b>Raio-x do mandato:</b> toque em uma faixa para filtrar</span>
<span id="raiox-num">100% do total</span></p>
<div class="barra-empilhada" role="group" aria-label="Divisão das {_num(total)} propostas por tipo">{segmentos}</div></div>
</div>
<div class="kpis" role="group" aria-label="Propostas por tipo">{kpis}</div>
</div>
</div></section>"""

    # ---------------- Seu bairro ----------------
    chips_g = '<button type="button" class="chip-filtro" data-aba="" aria-pressed="true">{}Todos</button>'.format(
        icone("check", "marca")) + "".join(
        f'<button type="button" class="chip-filtro" data-aba="{g}" aria-pressed="false">{icone("check", "marca")}{CURTO[g]}</button>'
        for g in ["melhoria", "cobranca", "lei", "homenagem"])
    lugares = "".join(f'<button type="button" class="chip-lugar" data-q="{esc(x)}">{esc(x)}</button>' for x in exemplos_lugar)
    bairro = f"""<section id="busca" class="secao" aria-labelledby="titulo-bairro">
<div class="container">
<h2 id="titulo-bairro">O que pediram pelo seu bairro?</h2>
<p class="sub">Digite o bairro, a rua ou a comunidade para ver quem levou o pedido à Câmara. Sem nada digitado, você vê a cidade inteira.</p>
<div class="controles">
<div class="linha-busca">
<label class="campo-busca"><span class="sr">Bairro, rua ou comunidade</span>{icone("location_on")}
<input id="q" type="search" autocomplete="off" placeholder="Ex.: Cavalhada, Junco, Avenida Sete de Setembro">
<button type="button" class="limpar" id="limpar-q" aria-label="Limpar a busca" hidden>{icone("close")}</button></label>
<div class="grupo-chips" role="group" aria-label="Filtrar por tipo de proposta">{chips_g}</div>
</div>
<div class="lugares"><span>Mais citados:</span>{lugares}</div>
</div>
<div id="painel" aria-live="polite"><p class="sub">Carregando as propostas…</p></div>
<noscript><p>A busca precisa de JavaScript. Você ainda pode ver cada vereador mais abaixo.</p></noscript>
</div></section>"""

    # ---------------- O problema que não some ----------------
    def painel_rep(i, x):
        ps = x["pedidos"]
        de, ate = mes_ano(ps[0]["d"]), mes_ano(ps[-1]["d"])
        quando = f"de {de} a {ate}" if de != ate else f"em {de}"
        n_aut = len(x["autores"])
        linha_tempo = "".join(
            f'<li><p class="lt-meta">{data_br(p["d"])} · {esc(p["tn"])} nº {p["n"]} · '
            f'{esc(", ".join(por_id[a]["nome"] for a in p["a"]))}</p>'
            f'<p>{esc(resumo(p["e"]))}</p>'
            f'<a class="link" href="{sapl}/materia/{p["i"]}">Ver na Câmara{icone("open_in_new")}</a></li>' for p in ps)
        return (f'<li class="rep{" oculto" if i >= 8 else ""}"><h3 class="rep-h">'
                f'<button type="button" class="rep-gatilho" aria-expanded="false" aria-controls="rep-{i}">'
                f'<span class="rep-n">{i + 1}</span>'
                f'<span class="rep-meio"><span class="rep-lugar">{esc(x["rua"])}</span>'
                f'{f"""<span class="rep-bairro">{esc(x["bairro"])}</span>""" if x["bairro"] else ""}'
                f'<span class="subtag">{icone(ICONE_ASSUNTO[x["assunto"]])}{esc(NOME_ASSUNTO[x["assunto"]])}</span>'
                f'<span class="rep-consenso">{n_aut} vereador{"es" if n_aut > 1 else ""} pediram · {quando}</span></span>'
                f'<span class="rep-dir"><span class="rep-conta">{len(ps)} pedidos</span>{icone("expand_more", "chevron")}</span>'
                f'</button></h3>'
                f'<div class="rep-painel" id="rep-{i}" hidden><ol class="linha-tempo">{linha_tempo}</ol>'
                f'<button type="button" class="botao-contorno" data-q="{esc(x["rua"])}">{icone("search")}Ver todos os pedidos dessa rua na busca</button>'
                f'</div></li>')
    reps_html = "".join(painel_rep(i, x) for i, x in enumerate(reps))
    mais = (f'<button type="button" class="botao-contorno" id="mais-reps" aria-expanded="false">{icone("unfold_more")}'
            f'<span>Ver todos os {len(reps)} lugares</span></button>' if len(reps) > 8 else "")
    repete = f"""<section id="problemas" class="secao" aria-labelledby="titulo-rep">
<div class="container">
<h2 id="titulo-rep">O problema que não some</h2>
<p class="sub">Ruas onde o mesmo assunto foi pedido {MIN_REPETE} vezes ou mais. Toque para ver cada pedido, em ordem de data.
Pedido repetido não prova que a Prefeitura ignorou: pode ser outro trecho da mesma rua ou um serviço refeito.</p>
<ol class="reps">{reps_html}</ol>{mais}
</div></section>"""

    # ---------------- Vereadores ----------------
    titulares = sum(v["titular"] for v in vereadores)
    suplentes = len(vereadores) - titulares

    def mini_barra(c):
        tot = sum(c[g] for g in QUATRO) or 1
        return "".join(f'<span class="g-{g}" style="flex:{c[g]}" title="{esc(GRUPOS[g][0])}: {c[g]}"></span>'
                       for g in QUATRO if c[g])

    def dados_ordem(v, c, resp, ped):
        pr = v["presenca"]
        pp = round(100 * pr["presente"] / pr["sessoes"]) if pr["sessoes"] else 0
        return (f'data-nome="{esc(v["nome"].lower())}" data-titular="{1 if v["titular"] else 0}" data-total="{len(v["propostas"])}" '
                f'data-presenca="{pp}" data-faltas="{len(pr["faltas"])}" data-lei="{c["lei"]}" data-cobranca="{c["cobranca"]}" '
                f'data-melhoria="{c["melhoria"]}" data-resp="{round(100 * resp / ped) if ped else 0}" data-tribuna="{len(v["discursos"])}"')

    cartoes, linhas = [], []
    for v in vereadores:
        c = collections.Counter(p["grupo"] for p in v["propostas"])
        resp, ped, _, _ = contas_situacao(v["propostas"])
        t = texto_presenca(v["presenca"])
        papel = "Titular" if v["titular"] else "Suplente"
        attrs = dados_ordem(v, c, resp, ped)
        cartoes.append(
            f'<li class="cracha" {attrs}><a class="cracha-link" href="vereador/{v["slug"]}.html" data-dossie="{v["id"]}">'
            f'<span class="cracha-cab">{foto(v, "")}<span class="cracha-id"><span class="cracha-nome">{esc(v["nome"])}</span>'
            f'<span class="cracha-meta">{esc(v["partido"])}<span class="papel{" suplente" if not v["titular"] else ""}">{papel}</span></span>'
            f'{f"""<span class="cargo">{esc(v["cargo"])}</span>""" if v["cargo"] else ""}</span></span>'
            f'<span class="metricas">'
            f'<span><span class="m-rot">Presença</span><b>{t[0] if t else "–"}%</b></span>'
            f'<span><span class="m-rot">Propostas</span><b>{len(v["propostas"])}</b></span>'
            f'<span><span class="m-rot">Pedidos respondidos</span><b>{round(100 * resp / ped) if ped else 0}%</b></span>'
            f'<span><span class="m-rot">Na tribuna</span><b>{len(v["discursos"])}</b></span></span>'
            f'<span class="mini-barra" aria-hidden="true">{mini_barra(c)}</span>'
            f'<span class="mini-rodape">{c["melhoria"]} melhorias · {c["cobranca"]} cobranças · {c["lei"]} leis · {c["homenagem"]} homenagens</span>'
            f'<span class="botao-tonal">{icone("person_search")}Ver dossiê</span></a></li>')
        linhas.append(
            f'<tr {attrs}><th scope="row"><a href="vereador/{v["slug"]}.html" data-dossie="{v["id"]}">{foto(v, "")}{esc(v["nome"])}</a></th>'
            f'<td>{esc(v["partido"])} · {papel}</td><td>{t[0] if t else "–"}%</td><td>{len(v["propostas"])}</td>'
            f'<td>{c["melhoria"]}</td><td>{c["cobranca"]}</td><td>{c["lei"]}</td><td>{c["homenagem"]}</td>'
            f'<td>{round(100 * resp / ped) if ped else 0}%</td><td>{len(v["discursos"])}</td></tr>')
    legenda = "".join(f'<span><i class="g-{g}"></i>{esc(GRUPOS[g][0])}</span>' for g in QUATRO)
    vereadores_html = f"""<section id="vereadores" class="secao" aria-labelledby="titulo-ver">
<div class="container">
<h2 id="titulo-ver">Os {titulares} vereadores (e {suplentes} suplentes)</h2>
<p class="sub">Presença, propostas e respostas da Prefeitura, com a mesma régua para todos. Toque em um vereador para abrir o dossiê.</p>
<div class="barra-ferramentas">
<div class="grupo-chips" role="group" aria-label="Filtrar por situação do mandato">
<button type="button" class="chip-filtro" data-papel="" aria-pressed="true">{icone("check", "marca")}Todos ({len(vereadores)})</button>
<button type="button" class="chip-filtro" data-papel="1" aria-pressed="false">{icone("check", "marca")}Titulares ({titulares})</button>
<button type="button" class="chip-filtro" data-papel="0" aria-pressed="false">{icone("check", "marca")}Suplentes ({suplentes})</button>
</div>
<div class="ferramentas-dir">
<label class="sr" for="ordem">Ordenar vereadores</label>
<select id="ordem" class="selecao">
<option value="nome">Ordenar: titulares primeiro (A–Z)</option><option value="total">Ordenar: mais propostas</option>
<option value="presenca">Ordenar: maior presença</option><option value="faltas">Ordenar: mais faltas</option>
<option value="lei">Ordenar: mais projetos de lei</option><option value="cobranca">Ordenar: mais cobranças</option>
<option value="resp">Ordenar: mais pedidos respondidos (%)</option><option value="tribuna">Ordenar: mais vezes na tribuna</option>
</select>
<div class="segmentado" role="group" aria-label="Modo de visualização">
<button type="button" id="ver-cartoes" aria-pressed="true">{icone("check", "marca")}{icone("grid_view")}Cartões</button>
<button type="button" id="ver-tabela" aria-pressed="false">{icone("check", "marca")}{icone("table_rows")}Tabela</button>
</div></div></div>
<p class="legenda-cores" aria-hidden="true">{legenda}</p>
<ul class="crachas" id="crachas">{"".join(cartoes)}</ul>
<div class="tabela-caixa" id="tabela" hidden><table class="tabela">
<caption class="sr">Comparação entre os vereadores</caption>
<thead><tr><th scope="col">Vereador</th><th scope="col">Partido · vínculo</th><th scope="col">Presença</th><th scope="col">Propostas</th>
<th scope="col">Melhorias</th><th scope="col">Cobranças</th><th scope="col">Leis</th><th scope="col">Homenagens</th>
<th scope="col">Respondidos</th><th scope="col">Tribuna</th></tr></thead>
<tbody id="linhas">{"".join(linhas)}</tbody></table></div>
</div></section>"""

    # ---------------- De onde vêm os números ----------------
    fontes = f"""<section id="fontes" class="secao" aria-labelledby="titulo-fontes">
<div class="container">
<h2 id="titulo-fontes">De onde vêm os números</h2>
<p class="sub">Tudo sai do sistema da própria Câmara Municipal de Cáceres, o SAPL. Nada é digitado à mão.</p>
<dl class="fontes">
<div><dt>Propostas</dt><dd>Indicações, requerimentos, moções e projetos, com seus autores, vêm da consulta pública do SAPL.
Conferimos o total de cada um dos 21 vereadores e 45 propostas sorteadas, uma a uma: todos batem.</dd></div>
<div><dt>Respostas da Prefeitura</dt><dd>Vêm da tramitação oficial de cada pedido. Resposta recebida não quer dizer problema resolvido.</dd></div>
<div><dt>Presença</dt><dd>Sessões ordinárias, pelas listas do SAPL, que batem com as atas. Licença não é falta: os períodos saem das Portarias da Câmara.</dd></div>
<div><dt>Grupos, assuntos e lugares</dt><dd>Regra automática, igual para todos, a partir do tipo oficial e do resumo. Pode errar em casos raros.
<a href="sobre.html#regra">Veja a regra</a>.</dd></div>
<div><dt>Votos</dt><dd>A Câmara não registra o voto de cada vereador desde agosto de 2020. Por isso não mostramos quem votou contra.</dd></div>
<div><dt>Salário e notas</dt><dd>Não mostramos estimativas nem damos nota a ninguém. Só entra o que tem fonte oficial.</dd></div>
</dl></div></section>"""

    dialogos = f"""<div class="veu" id="veu" hidden></div>
<div class="dossie" id="dossie" role="dialog" aria-modal="true" aria-labelledby="dossie-nome" hidden>
<div class="dossie-cab"><span class="dossie-rot">Dossiê do vereador</span>
<button type="button" class="botao-icone" id="fechar-dossie" aria-label="Fechar o dossiê">{icone("close")}</button></div>
<div class="dossie-corpo" id="dossie-corpo"></div>
<div class="dossie-rodape" id="dossie-rodape"></div></div>
<div class="busca-rapida" id="busca-rapida" role="dialog" aria-modal="true" aria-label="Busca rápida" hidden>
<div class="br-cab">{icone("search")}<label class="sr" for="br-q">Buscar vereador, bairro ou rua</label>
<input id="br-q" type="search" autocomplete="off" placeholder="Nome do vereador, bairro ou rua">
<button type="button" class="botao-icone" id="fechar-busca" aria-label="Fechar a busca">{icone("close")}</button></div>
<div class="br-res" id="br-res"></div></div>"""

    script = "<script>var CFG=" + json.dumps({"sapl": sapl}) + ";</script>\n<script>" + JS + "</script>"
    return panorama + bairro + repete + vereadores_html + fontes + dialogos + script


def dados(vereadores, coleta, dados_json):
    d = dados_json(vereadores, coleta)
    cb = collections.Counter(b for p in d["propostas"] for b in p["b"])
    cr = collections.Counter(r for p in d["propostas"] for r in p["r"])
    for p in d["propostas"]:
        bs = [b for b in p["b"] if cb[b] >= 3]
        rs = [r for r in p["r"] if cr[r] >= 2]
        lg = d["bairros"][max(bs, key=lambda b: cb[b])] if bs else (d["ruas"][max(rs, key=lambda r: cr[r])] if rs else "")
        if lg:
            p["lg"] = lg
    d["perfis"] = perfis(vereadores)
    d["grupos_curto"] = CURTO
    return d


JS = r"""
(function(){
var SAPL=CFG.sapl,D=null,est={q:"",g:"",s:"",x:""},mostrando=6;
var MES=["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"];
function norm(t){return (t||"").normalize("NFD").replace(/[̀-ͯ]/g,"").toLowerCase().replace(/[^a-z0-9]+/g," ").trim();}
function esc(t){return String(t==null?"":t).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});}
function num(n){return Number(n).toLocaleString("pt-BR");}
function data(d){if(!d)return"";var p=d.split("-");return +p[2]+" "+MES[+p[1]-1]+" "+p[0];}
function dataBR(d){return d?d.split("-").reverse().join("/"):"";}
function $(id){return document.getElementById(id);}
function ic(n,c){return '<span class="ms'+(c?' '+c:'')+'" aria-hidden="true">'+n+'</span>';}
function avatar(id,cl){var v=D.perfis[id];return v&&v.foto?'<img class="'+(cl||'av')+'" src="fotos/'+id+'.jpg" alt="" width="32" height="32">':'<span class="'+(cl||'av')+'"></span>';}

/* ---------- Busca por bairro ---------- */
function filtrar(){
  var q=norm(est.q),re=q?new RegExp("(^| )"+q.replace(/ /g," +")+"( |$)"):null;
  return D.propostas.filter(function(p){return (!est.g||p.g===est.g)&&(!est.s||p.s.indexOf(est.s)>=0)&&(!est.x||p.x===est.x)&&(!re||re.test(p._n));});
}
function lugar(p){return p.lg||"";}
function cartao(p){
  var lg=lugar(p),ic0=p.s.length?D.icones[p.s[0]]:D.icones["g_"+p.g];
  var autores=p.a.slice(0,3).map(function(a){var v=D.perfis[a];return '<a class="autor" href="vereador/'+v.slug+'.html" data-dossie="'+a+'">'+avatar(a)+esc(v.nome)+'</a>';}).join("")+(p.a.length>3?'<span class="mais-aut">+'+(p.a.length-3)+'</span>':'');
  var termo=D.explica_tipo[p.tn]?'<button type="button" class="termo" aria-expanded="false" data-explica="'+esc(D.explica_tipo[p.tn])+'">'+esc(p.tn)+' nº '+p.n+ic("help")+'</button>':'<span>'+esc(p.tn)+' nº '+p.n+'</span>';
  var sitb=p.x?'<button type="button" class="termo sit s-'+p.x+'" aria-expanded="false" data-explica="'+esc(D.explica_situacao[p.x]+' Última movimentação oficial: '+p.xs+'.')+'">'+ic(D.icones["x_"+p.x])+esc(p.xr)+ic("help")+'</button>':'';
  return '<li class="prop"><div class="prop-topo"><button type="button" class="badge g-'+p.g+'" data-g="'+p.g+'" aria-label="Filtrar: '+esc(D.grupos[p.g])+'">'+ic(ic0)+esc(D.grupos_curto[p.g])+'</button>'
    +(lg?'<button type="button" class="prop-lugar" data-q="'+esc(lg)+'">'+ic("location_on")+esc(lg)+'</button>':'')+'</div>'
    +'<p class="ementa" tabindex="0" role="button" aria-expanded="false" data-curto="'+esc(p.rs||p.e)+'" data-longo="'+esc(p.e)+'">'+esc(p.rs||p.e||"Sem resumo no sistema oficial.")+'</p>'
    +'<p class="prop-meta"><span>'+data(p.d)+'</span>'+termo+sitb+'</p><p class="explica-termo" hidden></p>'
    +'<div class="prop-rodape"><div class="autores">'+autores+'</div><a class="link" href="'+SAPL+'/materia/'+p.i+'">Ver na Câmara'+ic("open_in_new")+'<span class="sr"> (site oficial)</span></a></div></li>';
}
function ranking(c,n){return Object.keys(c).sort(function(a,b){return c[b]-c[a];}).slice(0,n);}
function lista(t,itens,max){
  if(!itens.length)return"";
  return '<div class="resumo-bloco"><h3>'+t+'</h3><ol class="ranking">'+itens.map(function(x){
    return '<li class="clicavel"><span class="r-nome">'+x[0]+'</span><b>'+num(x[1])+ic("chevron_right","seta")+'</b><i style="--w:'+Math.round(100*x[1]/max)+'%"></i></li>';}).join("")+'</ol></div>';
}
var NOME_X={respondido:"Prefeitura respondeu",aguardando:"Aguardando resposta"};
function desenhar(){
  var ach=filtrar(),out=$("painel"),qv=est.q.trim();
  document.querySelectorAll("#busca .chip-filtro").forEach(function(a){a.setAttribute("aria-pressed",a.getAttribute("data-aba")===est.g?"true":"false");});
  $("limpar-q").hidden=!est.q;
  var ativos=[];
  if(est.s)ativos.push('<button type="button" class="chip-ativo" data-limpa="s">Assunto: '+esc(D.assuntos[est.s])+ic("close")+'<span class="sr"> (tirar filtro)</span></button>');
  if(est.x)ativos.push('<button type="button" class="chip-ativo" data-limpa="x">Situação: '+esc(NOME_X[est.x]||est.x)+ic("close")+'<span class="sr"> (tirar filtro)</span></button>');
  var h=ativos.length?'<div class="ativos">'+ativos.join("")+'</div>':'';
  if(!ach.length){out.innerHTML=h+'<p class="vazio">Nenhuma proposta '+(qv?'cita “'+esc(qv)+'”':'com esses filtros')+'. Tente outro jeito de escrever ou tire um filtro.</p>';ligar();return;}
  var ped=ach.filter(function(p){return p.tn==="Indicação"||p.tn==="Requerimento";}),resp=0,agu=0;
  ped.forEach(function(p){if(p.x==="respondido")resp++;else if(p.x==="aguardando")agu++;});
  var onde=(est.g?'de '+esc(D.grupos[est.g].toLowerCase())+' ':'')+(qv?'que citam “'+esc(qv)+'”':'na cidade inteira');
  h+='<div class="meta-res"><p><b>'+num(ach.length)+'</b> propostas '+onde+'</p>';
  if(ped.length)h+='<p class="meta-resp">'+ic("mark_email_read")+'<b>'+num(resp)+'</b> de '+num(ped.length)+' pedidos com resposta da Prefeitura'+(agu?' · <b>'+num(agu)+'</b> aguardando':'')+'</p>';
  h+='</div>';
  if(ped.length&&!est.x)h+='<div class="atalhos-x">'+(resp?'<button type="button" class="chip-lugar" data-x="respondido">Só os respondidos</button>':'')+(agu?'<button type="button" class="chip-lugar" data-x="aguardando">Só os que aguardam resposta</button>':'')+'</div>';
  var pv={},pa={},pb={};ach.forEach(function(p){p.a.forEach(function(a){pv[a]=(pv[a]||0)+1;});p.s.forEach(function(s){pa[s]=(pa[s]||0)+1;});p.b.forEach(function(b){pb[b]=(pb[b]||0)+1;});});
  var tv=ranking(pv,5),ta=ranking(pa,5),tb=ranking(pb,5);
  h+='<details class="resumo-filtro"'+(window.innerWidth>=900?' open':'')+'><summary>Quem mais propôs, o que mais pedem e onde</summary><div class="resumo-grade">'
   +lista("Quem mais propôs",tv.map(function(a){var v=D.perfis[a];return ['<a class="esticado" href="vereador/'+v.slug+'.html" data-dossie="'+a+'">'+avatar(a)+esc(v.nome)+'</a>',pv[a]];}),pv[tv[0]]||1)
   +(est.s?'':lista("O que mais pedem",ta.map(function(s){return ['<button type="button" class="esticado" data-s="'+s+'">'+esc(D.assuntos[s])+'</button>',pa[s]];}),pa[ta[0]]||1))
   +(qv?'':lista("Bairros mais citados",tb.map(function(b){return ['<button type="button" class="esticado" data-q="'+esc(D.bairros[b])+'">'+esc(D.bairros[b])+'</button>',pb[b]];}),pb[tb[0]]||1))
   +'</div></details>';
  h+='<ol class="props">'+ach.slice(0,mostrando).map(cartao).join("")+'</ol>';
  if(ach.length>mostrando)h+='<button type="button" class="botao-contorno" id="mais-props">'+ic("expand_more")+'Mostrar mais '+Math.min(10,ach.length-mostrando)+' de '+num(ach.length-mostrando)+'</button>';
  out.innerHTML=h;ligar();
}
function salvar(){var h=[];if(est.q)h.push("q="+encodeURIComponent(est.q));["g","s","x"].forEach(function(k){if(est[k])h.push(k+"="+est[k]);});try{history.replaceState(null,"",h.length?"#"+h.join("&"):location.pathname);}catch(e){}}
function ir(m,rolar){for(var k in m)est[k]=m[k];$("q").value=est.q;mostrando=6;salvar();desenhar();marcarRaiox(est.g);if(rolar!==false)$("busca").scrollIntoView({behavior:"smooth"});}
function lerHash(){var h=location.hash.slice(1);if(!h||h==="busca"||h==="panorama")return;if(h.indexOf("=")<0)return;h.split("&").forEach(function(x){var p=x.split("=");if(p[0]==="q")est.q=decodeURIComponent(p[1]||"");if(/^[gsx]$/.test(p[0]))est[p[0]]=p[1]||"";});}
function ligar(){
  document.querySelectorAll("[data-q]").forEach(function(b){b.onclick=function(ev){ev.preventDefault();ir({q:b.getAttribute("data-q"),g:"",s:"",x:""});};});
  document.querySelectorAll("[data-g]").forEach(function(b){b.onclick=function(ev){ev.preventDefault();var g=b.getAttribute("data-g");ir(b.closest("#painel")?{g:g}:{q:"",g:g,s:"",x:""});};});
  document.querySelectorAll("[data-s]").forEach(function(b){b.onclick=function(){ir({s:b.getAttribute("data-s")});};});
  document.querySelectorAll("[data-x]").forEach(function(b){b.onclick=function(){ir({x:b.getAttribute("data-x")});};});
  document.querySelectorAll("[data-limpa]").forEach(function(b){b.onclick=function(){var m={};m[b.getAttribute("data-limpa")]="";ir(m);};});
  document.querySelectorAll("[data-dossie]").forEach(function(a){a.onclick=function(ev){if(!D)return;ev.preventDefault();abrirDossie(a.getAttribute("data-dossie"),a);};});
  var m=$("mais-props");if(m)m.onclick=function(){mostrando+=10;desenhar();};
  document.querySelectorAll(".termo").forEach(function(b){b.onclick=function(){
    var corpo=b.closest(".prop"),cx=corpo.querySelector(".explica-termo"),ab=b.getAttribute("aria-expanded")==="true";
    corpo.querySelectorAll(".termo").forEach(function(o){o.setAttribute("aria-expanded","false");});
    if(ab){cx.hidden=true;return;}b.setAttribute("aria-expanded","true");cx.textContent=b.dataset.explica;cx.hidden=false;};});
  document.querySelectorAll(".ementa").forEach(function(e){function t(){var a=e.classList.toggle("aberta");e.setAttribute("aria-expanded",a?"true":"false");e.textContent=a?(e.dataset.longo||e.dataset.curto):e.dataset.curto;}e.onclick=t;e.onkeydown=function(k){if(k.key==="Enter"||k.key===" "){k.preventDefault();t();}};});
}
document.querySelectorAll("#busca .chip-filtro").forEach(function(a){a.addEventListener("click",function(){ir({g:a.getAttribute("data-aba")},false);});});
$("q").addEventListener("input",function(){est.q=$("q").value;mostrando=6;salvar();if(D)desenhar();});
$("limpar-q").addEventListener("click",function(){est.q="";$("q").value="";salvar();desenhar();$("q").focus();});

/* ---------- Raio-x ---------- */
var segs=[].slice.call(document.querySelectorAll(".barra-empilhada .seg"));
function marcarRaiox(g){
  var barra=document.querySelector(".barra-empilhada");barra.classList.toggle("destaque",!!g);
  segs.forEach(function(s){s.classList.toggle("ativo",s.getAttribute("data-g")===g);});
  var alvo=segs.filter(function(s){return s.getAttribute("data-g")===g;})[0];
  $("raiox-rot").innerHTML=alvo?'<b>'+esc(alvo.getAttribute("aria-label").split(":")[0])+'</b>':'<b>Raio-x do mandato:</b> toque em uma faixa para filtrar';
  $("raiox-num").textContent=alvo?alvo.getAttribute("aria-label").split("(")[1].replace(")",""):"100% do total";
}
segs.forEach(function(s){var g=s.getAttribute("data-g");
  s.addEventListener("mouseenter",function(){marcarRaiox(g);});s.addEventListener("focus",function(){marcarRaiox(g);});
  s.addEventListener("mouseleave",function(){marcarRaiox(est.g);});s.addEventListener("blur",function(){marcarRaiox(est.g);});});

/* ---------- O problema que não some ---------- */
document.querySelectorAll(".rep-gatilho").forEach(function(b){b.addEventListener("click",function(){
  var ab=b.getAttribute("aria-expanded")==="true",p=$(b.getAttribute("aria-controls"));
  b.setAttribute("aria-expanded",ab?"false":"true");p.hidden=ab;b.closest(".rep").classList.toggle("aberto",!ab);});});
var mr=$("mais-reps");if(mr)mr.addEventListener("click",function(){var ab=mr.getAttribute("aria-expanded")==="true";
  document.querySelectorAll(".rep").forEach(function(r,i){if(i>=8)r.classList.toggle("oculto",ab);});
  mr.setAttribute("aria-expanded",ab?"false":"true");mr.querySelector("span:last-child").textContent=ab?mr.dataset.mais:"Mostrar menos";});
if(mr)mr.dataset.mais=mr.querySelector("span:last-child").textContent;

/* ---------- Vereadores ---------- */
var lista1=$("crachas"),cart=[].slice.call(lista1.children),corpoT=$("linhas"),linT=[].slice.call(corpoT.children),papel="";
function ordenar(){
  var o=$("ordem").value;
  function cmp(a,b){if(o==="nome")return (b.dataset.titular-a.dataset.titular)||a.dataset.nome.localeCompare(b.dataset.nome,"pt");
    return (+b.dataset[o])-(+a.dataset[o])||a.dataset.nome.localeCompare(b.dataset.nome,"pt");}
  [[cart,lista1],[linT,corpoT]].forEach(function(par){par[0].sort(cmp).forEach(function(el){el.hidden=papel!==""&&el.dataset.titular!==papel;par[1].appendChild(el);});});
}
$("ordem").addEventListener("change",ordenar);
document.querySelectorAll("#vereadores .chip-filtro").forEach(function(c){c.addEventListener("click",function(){papel=c.getAttribute("data-papel");
  document.querySelectorAll("#vereadores .chip-filtro").forEach(function(o){o.setAttribute("aria-pressed",o===c?"true":"false");});ordenar();});});
function modo(t){$("ver-cartoes").setAttribute("aria-pressed",t?"false":"true");$("ver-tabela").setAttribute("aria-pressed",t?"true":"false");lista1.hidden=t;$("tabela").hidden=!t;}
$("ver-cartoes").addEventListener("click",function(){modo(false);});$("ver-tabela").addEventListener("click",function(){modo(true);});
ordenar();

/* ---------- Diálogos: dossiê e busca rápida ---------- */
var ultimoFoco=null,aberto=null;
function focaveis(el){return [].slice.call(el.querySelectorAll('a[href],button:not([disabled]),input,select,[tabindex="0"]')).filter(function(x){return x.offsetParent!==null;});}
function abrir(el,foco){ultimoFoco=document.activeElement;aberto=el;$("veu").hidden=false;el.hidden=false;document.body.classList.add("travado");
  requestAnimationFrame(function(){el.classList.add("aberto");$("veu").classList.add("aberto");(foco||focaveis(el)[0]).focus();});}
function fechar(){if(!aberto)return;var el=aberto;aberto=null;el.classList.remove("aberto");$("veu").classList.remove("aberto");document.body.classList.remove("travado");
  setTimeout(function(){el.hidden=true;$("veu").hidden=true;},250);if(ultimoFoco)ultimoFoco.focus();}
document.addEventListener("keydown",function(e){
  if(e.key==="Escape"&&aberto){fechar();return;}
  if(e.key==="Tab"&&aberto){var f=focaveis(aberto);if(!f.length)return;if(e.shiftKey&&document.activeElement===f[0]){e.preventDefault();f[f.length-1].focus();}else if(!e.shiftKey&&document.activeElement===f[f.length-1]){e.preventDefault();f[0].focus();}}
  if(!aberto&&((e.key==="k"&&(e.metaKey||e.ctrlKey))||(e.key==="/"&&!/input|textarea|select/i.test(document.activeElement.tagName)))){e.preventDefault();abrirBusca();}
});
$("veu").addEventListener("click",fechar);$("fechar-dossie").addEventListener("click",fechar);$("fechar-busca").addEventListener("click",fechar);

function barraGrupo(rot,n,max,g,slug){return '<li><a href="vereador/'+slug+'.html#'+g+'"><span>'+rot+'</span><b>'+n+'</b><i class="g-'+g+'" style="--w:'+Math.round(100*n/(max||1))+'%"></i></a></li>';}
function abrirDossie(id,orig){
  var v=D.perfis[id];if(!v)return;var pr=v.presenca,pp=pr.sessoes?Math.round(100*pr.presente/pr.sessoes):0;
  var gm=Math.max.apply(null,["melhoria","cobranca","homenagem","lei"].map(function(g){return v.grupos[g];}));
  var porId={};D.propostas.forEach(function(p){porId[p.i]=p;});
  var lic=pr.licencas.map(function(l){return '<li>'+dataBR(l.inicio)+' a '+dataBR(l.fim)+': '+esc(l.motivo)+'</li>';}).join("");
  $("dossie-corpo").innerHTML='<div class="d-perfil">'+avatar(id,"d-foto")+'<div><h2 id="dossie-nome">'+esc(v.nome)+'</h2><p class="sub">'+esc(v.completo)+'</p>'
    +'<p class="cracha-meta">'+esc(v.partido)+'<span class="papel'+(v.titular?'':' suplente')+'">'+(v.titular?'Titular':'Suplente')+'</span></p>'+(v.cargo?'<span class="cargo">'+esc(v.cargo)+'</span>':'')+'</div></div>'
    +'<div class="d-numeros"><div><span class="m-rot">Presença</span><b>'+pp+'%</b><span class="m-det">'+pr.presente+' de '+pr.sessoes+' sessões · '+pr.faltas+' falta'+(pr.faltas===1?'':'s')+'</span></div>'
    +'<div><span class="m-rot">Propostas</span><b>'+v.total+'</b><span class="m-det">'+v.discursos+' vezes na tribuna</span></div>'
    +'<div><span class="m-rot">Respondidos</span><b>'+(v.pedidos?Math.round(100*v.respondidos/v.pedidos):0)+'%</b><span class="m-det">'+v.respondidos+' de '+v.pedidos+' pedidos</span></div></div>'
    +(lic?'<div class="d-bloco"><h3>Licenças (não contam como falta)</h3><ul class="d-lic">'+lic+'</ul></div>':'')
    +'<div class="d-bloco"><h3>O que propôs</h3><ul class="d-barras">'
    +["melhoria","cobranca","homenagem","lei"].map(function(g){return barraGrupo(esc(D.grupos[g]),v.grupos[g],gm,g,v.slug);}).join("")
    +'</ul>'+(v.leis?'<p class="m-det">'+v.viraram+' de '+v.leis+' projetos de lei viraram lei.</p>':'')+'</div>'
    +'<div class="d-bloco"><h3>Propostas mais recentes</h3><ol class="d-recentes">'+v.recentes.map(function(i){var p=porId[i];if(!p)return"";
      return '<li><p class="lt-meta">'+data(p.d)+' · '+esc(p.tn)+' nº '+p.n+(p.xr?' · '+esc(p.xr):'')+'</p><p>'+esc(p.rs||p.e)+'</p><a class="link" href="'+SAPL+'/materia/'+p.i+'">Ver na Câmara'+ic("open_in_new")+'</a></li>';}).join("")+'</ol></div>';
  $("dossie-rodape").innerHTML='<a class="botao-cheio" href="vereador/'+v.slug+'.html">'+ic("person")+'Página completa</a><a class="botao-contorno" href="'+SAPL+'/parlamentar/'+id+'">Ficha na Câmara'+ic("open_in_new")+'</a>';
  abrir($("dossie"),$("fechar-dossie"));
}
function abrirBusca(){$("br-q").value="";resultados("");abrir($("busca-rapida"),$("br-q"));}
function resultados(q){
  var n=norm(q),h="";
  var vs=Object.keys(D.perfis).filter(function(id){return !n||norm(D.perfis[id].nome+" "+D.perfis[id].completo+" "+D.perfis[id].partido).indexOf(n)>=0;}).slice(0,n?8:6);
  if(vs.length)h+='<p class="br-grupo">Vereadores</p>'+vs.map(function(id){var v=D.perfis[id];return '<button type="button" class="br-item" data-ver="'+id+'">'+avatar(id)+'<span>'+esc(v.nome)+'<small>'+esc(v.partido)+' · '+v.total+' propostas</small></span>'+ic("chevron_right","seta")+'</button>';}).join("");
  if(n.length>=2){var ls=[];[D.bairros,D.ruas].forEach(function(m){Object.keys(m).forEach(function(k){if(k.indexOf(n)>=0&&ls.indexOf(m[k])<0)ls.push(m[k]);});});
    if(ls.length)h+='<p class="br-grupo">Bairros e ruas</p>'+ls.slice(0,8).map(function(l){return '<button type="button" class="br-item" data-lugar="'+esc(l)+'">'+ic("location_on")+'<span>'+esc(l)+'</span>'+ic("chevron_right","seta")+'</button>';}).join("");}
  $("br-res").innerHTML=h||'<p class="vazio">Nada encontrado para “'+esc(q)+'”.</p>';
  $("br-res").querySelectorAll("[data-ver]").forEach(function(b){b.onclick=function(){var id=b.getAttribute("data-ver");fechar();setTimeout(function(){abrirDossie(id);},260);};});
  $("br-res").querySelectorAll("[data-lugar]").forEach(function(b){b.onclick=function(){fechar();ir({q:b.getAttribute("data-lugar"),g:"",s:"",x:""});};});
}
$("br-q").addEventListener("input",function(){resultados($("br-q").value);});
var gatilho=$("abrir-busca");if(gatilho)gatilho.addEventListener("click",function(ev){if(!D)return;ev.preventDefault();abrirBusca();});

/* ---------- Carga ---------- */
fetch("dados.json").then(function(r){return r.json();}).then(function(d){
  d.propostas.forEach(function(p){p._n=norm(p.e);});D=d;lerHash();$("q").value=est.q;desenhar();marcarRaiox(est.g);ligar();
  if(location.hash==="#buscar")abrirBusca();else if(est.q||est.g||est.s||est.x)$("busca").scrollIntoView();
}).catch(function(){$("painel").innerHTML='<p class="vazio">Não foi possível carregar as propostas. Recarregue a página.</p>';});
ligar();
var calmo=window.matchMedia&&matchMedia("(prefers-reduced-motion: reduce)").matches;
if(!calmo)document.querySelectorAll("[data-conta]").forEach(function(b){var fim=+b.getAttribute("data-conta"),t0=null;
  function passo(t){if(!t0)t0=t;var k=Math.min(1,(t-t0)/1100);k=1-Math.pow(1-k,3);b.textContent=Math.round(fim*k).toLocaleString("pt-BR");if(k<1)requestAnimationFrame(passo);}requestAnimationFrame(passo);});
})();
"""
