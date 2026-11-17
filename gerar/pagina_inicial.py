"""Página inicial do Radar Cáceres e o arquivo de dados usado pela busca."""
import collections
import json

from assuntos import ASSUNTOS, assuntos
from classificar import GRUPOS, ORDEM as ORDEM_GRUPOS
from locais import Rotulos, bairros, ruas
import situacao as sit

SIGLA = {
    "Indicação": "IND", "Requerimento": "REQ", "Moção": "MOC", "Projeto de Lei": "PL",
    "Projeto de Lei Complementar": "PLC", "Projeto de Resolução": "PR", "Projeto de Decreto Legislativo": "PDL",
    "Proposta de Emenda à Lei Orgânica": "PELO", "Emenda Parlamentar": "EMD",
}
NOME_ASSUNTO = {c: n for c, n, _ in ASSUNTOS}
# Ícones Material Symbols para cada assunto e grupo.
ICONE_ASSUNTO = {"iluminacao": "lightbulb", "asfalto": "add_road", "estrada": "landscape", "limpeza": "cleaning_services",
                 "agua": "water_drop", "drenagem": "flood", "transito": "traffic", "saude": "local_hospital",
                 "educacao": "school", "lazer": "park", "arvores": "forest", "transporte": "directions_bus"}
ICONE_GRUPO = {"melhoria": "construction", "cobranca": "contact_support", "homenagem": "celebration",
               "lei": "gavel", "outros": "more_horiz"}


def icone(nome, extra=""):
    return f'<span class="ms{(" " + extra) if extra else ""}" aria-hidden="true">{nome}</span>'
MIN_REPETE = 3


def montar(vereadores):
    """Junta as propostas de todos os vereadores, sem repetir as assinadas em conjunto."""
    rr, rb = Rotulos(), Rotulos()
    props = {}
    for v in vereadores:
        for p in v["propostas"]:
            item = props.get(p["id"])
            if item is None:
                eh_pedido = p["grupo"] in ("melhoria", "cobranca")
                item = props[p["id"]] = {
                    "i": p["id"], "t": SIGLA.get(p["tipo"], p["tipo"]), "tn": p["tipo"],
                    "n": f'{p["numero"]}/{p["ano"]}', "d": p["data"], "e": p["ementa"], "g": p["grupo"],
                    "s": assuntos(p["ementa"]) if eh_pedido else [],
                    "x": p.get("situacao") or "", "xr": rotulo_situacao(p), "xs": p.get("status", ""),
                    "r": rr.anotar(ruas(p["ementa"])) if eh_pedido else [],
                    "b": rb.anotar(bairros(p["ementa"])) if eh_pedido else [],
                    "a": [],
                }
            item["a"].append(v["id"])
    lista = sorted(props.values(), key=lambda x: (x["d"] or "", x["i"]), reverse=True)
    rotulos_rua = {k: rr.rotulo(k) for k in rr.contagem}
    rotulos_bairro = {k: rb.rotulo(k) for k in rb.contagem}
    return lista, rotulos_rua, rotulos_bairro


def repetidos(lista, rotulos_rua, rotulos_bairro):
    """Mesmo assunto pedido várias vezes para a mesma rua."""
    grupos = collections.defaultdict(list)
    for p in lista:
        for r in p["r"]:
            for s in p["s"]:
                grupos[(r, s)].append(p)
    saida = []
    for (r, s), ps in grupos.items():
        if len(ps) < MIN_REPETE:
            continue
        datas = sorted(p["d"] for p in ps if p["d"])
        bairro = collections.Counter(b for p in ps for b in p["b"]).most_common(1)
        autores = {a for p in ps for a in p["a"]}
        saida.append({
            "rua": rotulos_rua[r], "bairro": rotulos_bairro[bairro[0][0]] if bairro else "",
            "assunto": NOME_ASSUNTO[s], "icone": ICONE_ASSUNTO[s], "vezes": len(ps), "autores": len(autores),
            "de": datas[0] if datas else "", "ate": datas[-1] if datas else "",
        })
    saida.sort(key=lambda x: (-x["vezes"], -x["autores"], x["rua"]))
    return saida


def dados_json(vereadores, coleta):
    lista, rr, rb = montar(vereadores)
    return {
        "coleta": coleta,
        "grupos": {g: GRUPOS[g][0] for g in ORDEM_GRUPOS},
        "assuntos": NOME_ASSUNTO,
        "icones": {**ICONE_ASSUNTO, **{"g_" + g: i for g, i in ICONE_GRUPO.items()},
                   **{"x_" + k: i for k, i in sit.ICONE.items()}},
        "ruas": rr,
        "bairros": rb,
        "vereadores": {v["id"]: {"nome": v["nome"], "partido": v["partido"], "slug": v["slug"],
                                 "foto": v["foto"]} for v in vereadores},
        "propostas": lista,
    }


TIPOS_LEI_DE_FATO = {"Projeto de Lei", "Projeto de Lei Complementar", "Proposta de Emenda à Lei Orgânica"}


def rotulo_situacao(p):
    x = p.get("situacao")
    if x == sit.VIROU_NORMA and p["tipo"] not in TIPOS_LEI_DE_FATO:
        return "Aprovado"
    return sit.ROTULO.get(x, "")


def etiqueta_situacao(p, esc):
    x = p.get("situacao")
    if not x:
        return ""
    return (f' <span class="sit s-{x}" title="Última movimentação oficial: {esc(p.get("status", ""))}">'
            f'{icone(sit.ICONE[x])}{esc(rotulo_situacao(p))}</span>')


def contas_situacao(propostas):
    pedidos = [p for p in propostas if p["tipo"] in sit.TIPOS_PEDIDO]
    leis = [p for p in propostas if p["tipo"] in TIPOS_LEI_DE_FATO]
    return (sum(p["situacao"] == sit.RESPONDIDO for p in pedidos), len(pedidos),
            sum(p["situacao"] == sit.VIROU_NORMA for p in leis), len(leis))


def resumo_situacao(propostas, esc):
    resp, ped, viraram, leis = contas_situacao(propostas)
    partes = []
    if ped:
        partes.append(f"{resp} de {ped} pedidos já têm resposta escrita da Prefeitura")
    if leis:
        partes.append(f"{viraram} de {leis} projetos de lei viraram lei")
    return f'<p class="sub">{esc(" · ".join(partes))}.</p>' if partes else ""


def texto_presenca(pr):
    if not pr or not pr["sessoes"]:
        return ""
    pct = round(100 * pr["presente"] / pr["sessoes"])
    j, f = len(pr["justificadas"]), len(pr["faltas"])
    return pct, (f'{pr["presente"]} de {pr["sessoes"]} {"sessão" if pr["sessoes"] == 1 else "sessões"} até agora',
                 f'{j} ausência{"s" if j != 1 else ""} justificada{"s" if j != 1 else ""} · {f} falta{"s" if f != 1 else ""}')


def bloco_presenca(v, esc, data_br, sapl):
    pr = v.get("presenca")
    t = texto_presenca(pr)
    if not t:
        return ""
    pct, (linha1, linha2) = t
    faltas = "".join(f'<li><a href="{sapl}/sessao/{sid}">{data_br(d)}</a></li>' for sid, d in pr["faltas"])
    justif = "".join(f'<li><a href="{sapl}/sessao/{sid}">{data_br(d)}</a></li>' for sid, d in pr["justificadas"])
    def normas(item):
        return ", ".join(f'<a href="{sapl}/norma/{nid}">{esc(nome)}</a>' if nid else esc(nome) for nome, nid in item["normas"].items())
    lic = "".join(f'<li>{data_br(l["inicio"])} a {data_br(l["fim"])}: {esc(l["motivo"])} ({normas(l)})</li>' for l in pr["licencas"])
    ex = pr.get("exercicio")
    ex_html = (f'<p class="sub">Em exercício por convocação: {normas(ex)}.'
               f'{(" " + esc(ex["obs"])) if ex.get("obs") else ""}</p>') if ex else ""
    return f"""<section class="presenca" id="presenca"><h2>Presença nas sessões ordinárias</h2>
<p class="pct"><b>{pct}%</b> <span>{esc(linha1)}</span></p><p class="sub">{esc(linha2)}</p>
{f'<h3>Faltas</h3><ul class="datas">{faltas}</ul>' if faltas else ""}
{f'<h3>Ausências justificadas</h3><ul class="datas">{justif}</ul>' if justif else ""}
{f'<h3>Licenças (não contam como falta)</h3><ul class="lic">{lic}</ul>' if lic else ""}{ex_html}
<p class="nota">Presente na lista de abertura ou na da Ordem do Dia conta como presente. Sessões em licença não contam.
<a href="../index.html#fontes">Como contamos</a>.</p></section>"""


def nome_proprio(nome):
    """'ELIS FERNANDA DE MELO SILVA' -> 'Elis Fernanda de Melo Silva'."""
    pequenas = {"da", "de", "do", "das", "dos", "e"}
    return " ".join(p if p in pequenas else p.capitalize() for p in (nome or "").lower().split())


def _num(n):
    return f"{n:,}".replace(",", ".")


MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def mes_ano(iso):
    if not iso:
        return ""
    a, m, _ = iso.split("-")
    return f"{MESES[int(m) - 1]} {a}"


def gerar(vereadores, coleta_br, esc, foto, periodo, sapl, anos, exemplos_lugar):
    lista, rr, rb = montar(vereadores)
    cont = collections.Counter(p["g"] for p in lista)
    total = len(lista)
    reps = repetidos(lista, rr, rb)

    # ---------- Topo ----------
    contadores = "".join(
        f'<div class="contador g-{g}"><b data-conta="{cont[g]}">{_num(cont[g])}</b><span>{esc(rotulo)}</span></div>'
        for g, rotulo in (("melhoria", "pedidos de melhoria nos bairros"), ("cobranca", "perguntas e cobranças"),
                          ("homenagem", "homenagens"), ("lei", "projetos de lei e regras")))
    topo = f"""<section class="hero entra">
<p class="selo">Dados oficiais · última conferência em {coleta_br}</p>
<h1 class="tit-hero">O que cada vereador de Cáceres <em>fez</em> desde a posse.</h1>
<p class="lead">Tudo que os vereadores apresentaram na Câmara em {" e ".join(anos)}, organizado para qualquer
pessoa entender. Cada número leva ao documento oficial.</p>
<div class="radar-total">
<div class="radar" aria-hidden="true"><span class="anel a1"></span><span class="anel a2"></span><span class="anel a3"></span><span class="feixe"></span><span class="eco e1"></span><span class="eco e2"></span></div>
<div class="radar-num"><b data-conta="{total}">{_num(total)}</b><span>propostas apresentadas pelos vereadores até agora</span></div>
</div>
<div class="contadores">{contadores}</div>
<p class="nota">O robô volta ao sistema da Câmara toda madrugada. <a href="#fontes">De onde vêm os números</a></p>
</section>"""

    # ---------- Busca ----------
    chips = "".join(f'<button type="button" class="chip" data-q="{esc(x)}">{icone("location_on")}{esc(x)}</button>' for x in exemplos_lugar)
    curtos = {"melhoria": "Pedidos", "cobranca": "Cobranças", "homenagem": "Homenagens", "lei": "Leis", "outros": "Outros"}
    abas = '<button type="button" class="aba" data-aba="" aria-pressed="true">Todos</button>' + "".join(
        f'<button type="button" class="aba" data-aba="{g}" aria-pressed="false">{curtos[g]}</button>'
        for g in ORDEM_GRUPOS[:4])
    busca = f"""<section id="busca" class="secao entra">
<h2>O que pediram pelo seu bairro?</h2>
<p class="sub">Digite o bairro, a rua ou a comunidade. Sem nada digitado, você vê a cidade inteira.</p>
<label class="campo-busca"><span class="sr">Bairro, rua ou comunidade</span>
{icone("search")}
<input id="q" type="search" autocomplete="off" placeholder="Digite seu bairro ou sua rua"></label>
<div class="chips">{chips}</div>
<div class="abas" role="group" aria-label="Filtrar por tipo de proposta">{abas}</div>
<div id="painel" class="painel" aria-live="polite"><p class="sub">Carregando as propostas…</p></div>
<noscript><p>A busca precisa de JavaScript. Você ainda pode ver cada vereador mais abaixo.</p></noscript>
</section>"""

    # ---------- Problema que não some ----------
    def cartao_rep(x, escondido):
        lugar = f'<span class="bairro">{esc(x["bairro"])}</span>' if x["bairro"] else ""
        periodo_txt = (f'de {mes_ano(x["de"])} a {mes_ano(x["ate"])}' if mes_ano(x["de"]) != mes_ano(x["ate"])
                       else f'em {mes_ano(x["de"])}')
        return (f'<li class="rep{" oculto" if escondido else ""}"><div class="vezes"><b>{x["vezes"]}</b><span>vezes</span></div>'
                f'<div><p class="rua">{esc(x["rua"])}</p>{lugar}<span class="tag">{icone(x["icone"])}{esc(x["assunto"])}</span>'
                f'<p class="meta">{x["autores"]} vereador{"es" if x["autores"] > 1 else ""} pediram · {periodo_txt}</p>'
                f'<button type="button" class="link" data-q="{esc(x["rua"])}">Ver os pedidos →</button></div></li>')
    reps_html = "".join(cartao_rep(x, i >= 6) for i, x in enumerate(reps))
    mais_reps = (f'<button type="button" class="botao" id="mais-reps">Mostrar mais ruas ({len(reps) - 6} na fila)</button>'
                 if len(reps) > 6 else "")
    repete = f"""<section class="secao entra">
<h2>O problema que não some</h2>
<p class="sub">Quando o mesmo assunto volta várias vezes para a mesma rua, pode ser sinal de que o problema
continua lá. O site da Câmara mostra cada pedido sozinho; aqui eles são cruzados um por um.</p>
<ol class="reps">{reps_html}</ol>{mais_reps}
<p class="aviso-curto">Pedido repetido não prova que a Prefeitura ignorou: pode ser outro trecho da mesma rua,
um serviço que precisou ser refeito ou vereadores diferentes pedindo a mesma coisa. Abra os pedidos e leia.</p>
</section>"""

    # ---------- Homenagem ou trabalho ----------
    cartoes_grupo = "".join(
        f'<li class="grupo g-{g}">{icone(ICONE_GRUPO[g], "ic-grupo")}<b>{_num(cont[g])}</b><p class="nome-grupo">{esc(GRUPOS[g][0])}</p>'
        f'<p class="sub">{esc(GRUPOS[g][1])}</p>'
        f'<button type="button" class="link" data-g="{g}">Ver todas →</button></li>'
        for g in ORDEM_GRUPOS if cont[g])
    trabalho = f"""<section class="secao entra">
<h2>Homenagem ou trabalho?</h2>
<p class="sub">São {_num(total)} propostas até agora. Toque em um grupo para ler cada uma.
A regra é a mesma para todos: <a href="sobre.html#regra">veja como separamos</a>.</p>
<ul class="grupos">{cartoes_grupo}</ul>
</section>"""

    # ---------- Crachás ----------
    partidos = collections.Counter(v["partido"] for v in vereadores if v["partido"])
    opcoes_partido = "".join(f'<option value="{esc(p)}">{esc(p)} ({n})</option>' for p, n in sorted(partidos.items()))

    def cracha(v):
        c = collections.Counter(p["grupo"] for p in v["propostas"])
        maior = max([c[g] for g in ORDEM_GRUPOS] + [1])
        linhas = "".join(
            f'<li class="g-{g}"><a href="vereador/{v["slug"]}.html#{g}"><span>{esc(GRUPOS[g][0])}</span><b>{c[g]}</b>'
            f'<i style="--w:{100 * c[g] / maior:.0f}%"></i></a></li>' for g in ORDEM_GRUPOS if c[g] or g != "outros")
        dados = " ".join(f'data-{g}="{c[g]}"' for g in ORDEM_GRUPOS)
        dados += f' data-viraram="{contas_situacao(v["propostas"])[2]}" data-faltas="{len(v["presenca"]["faltas"])}"'
        return (f'<li class="cracha" data-nome="{esc(v["nome"].lower())}" data-partido="{esc(v["partido"])}" '
                f'data-total="{len(v["propostas"])}" data-titular="{1 if v["titular"] else 0}" {dados}>'
                f'<div class="cab">{foto(v, "")}<div><h3 class="nome"><a href="vereador/{v["slug"]}.html">{esc(v["nome"])}</a></h3>'
                f'<p class="sub">{esc(nome_proprio(v["nome_completo"]))}</p>'
                f'<p class="partido">{esc(v["partido"])}{" · " if v["partido"] else ""}{esc(periodo(v))}</p>'
                f'{f"""<p class="cargo">{esc(v["cargo"])}</p>""" if v["cargo"] else ""}</div></div>'
                f'{presenca_cracha(v)}'
                f'<p class="total"><b>{len(v["propostas"])}</b> propostas até agora</p>'
                f'<p class="rot">O que propôs</p><ul class="barras">{linhas}</ul>{resultado(v)}'
                f'<a class="ficha" href="{sapl}/parlamentar/{v["id"]}">Ficha oficial na Câmara{icone("open_in_new")}</a></li>')
    def presenca_cracha(v):
        t = texto_presenca(v.get("presenca"))
        if not t:
            return ""
        pct, (l1, l2) = t
        return (f'<a class="pres" href="vereador/{v["slug"]}.html#presenca"><b>{pct}%</b>'
                f'<span>de presença · {esc(l1)}</span><span class="sub">{esc(l2)}</span></a>')

    def resultado(v):
        resp, ped, viraram, leis = contas_situacao(v["propostas"])
        itens = []
        if ped:
            itens.append(f'<li><span>Pedidos com resposta da Prefeitura</span><b>{resp} de {ped}</b>'
                         f'<i style="--w:{100 * resp / ped:.0f}%"></i></li>')
        if leis:
            itens.append(f'<li><span>Projetos de lei que viraram lei</span><b>{viraram} de {leis}</b>'
                         f'<i style="--w:{100 * viraram / leis:.0f}%"></i></li>')
        return f'<p class="rot">O que aconteceu</p><ul class="resultado">{"".join(itens)}</ul>' if itens else ""

    crachas = "".join(cracha(v) for v in vereadores)
    titulares = sum(v["titular"] for v in vereadores)
    vereadores_html = f"""<section id="vereadores" class="secao entra">
<h2>Os {titulares} vereadores</h2>
<p class="sub">E os {len(vereadores) - titulares} suplentes que já assumiram uma vaga. Toque nos números do crachá para ver cada proposta.</p>
<div class="filtros">
<label>Buscar por nome<input id="f-nome" type="search" autocomplete="off"></label>
<label>Partido<select id="f-partido"><option value="">Todos</option>{opcoes_partido}</select></label>
<label>Ordenar por<select id="f-ordem">
<option value="nome">Titulares primeiro (A–Z)</option><option value="total">Mais propostas</option>
<option value="melhoria">Mais pedidos de melhoria</option><option value="cobranca">Mais perguntas e cobranças</option>
<option value="lei">Mais projetos de lei</option><option value="viraram">Mais projetos que viraram lei</option><option value="faltas">Quem mais faltou</option><option value="homenagem">Mais homenagens</option></select></label>
</div>
<p class="sub" id="f-conta"></p>
<ul class="crachas" id="crachas">{crachas}</ul>
</section>"""

    fontes = f"""<section id="fontes" class="secao entra">
<h2>De onde vêm os números</h2>
<p class="sub">Tudo sai do sistema da própria Câmara Municipal de Cáceres, o SAPL. Nada é digitado à mão.</p>
<dl class="fontes">
<div><dt>Propostas</dt><dd>Cada indicação, requerimento, moção e projeto, com seus autores, vem da consulta pública do SAPL.
Em 17/11/2026 conferimos o total de cada um dos 21 vereadores e 45 propostas sorteadas, uma a uma: todos batem.</dd></div>
<div><dt>Grupos e assuntos</dt><dd>Uma regra automática, igual para todos, separa as propostas pelo tipo oficial e por palavras do resumo.
Pode errar em casos raros. <a href="sobre.html#regra">Veja a regra</a>.</dd></div>
<div><dt>Bairros e ruas</dt><dd>Lidos do resumo oficial de cada pedido. Se o resumo não cita o lugar, o pedido não aparece na busca.</dd></div>
<div><dt>Respostas da Prefeitura</dt><dd>Vêm da tramitação oficial de cada pedido: a Câmara registra quando manda o ofício
e quando recebe a resposta. Resposta recebida não quer dizer problema resolvido. Conferimos 12 propostas sorteadas com o SAPL: todas batem.</dd></div>
<div><dt>Presença</dt><dd>Conta as sessões ordinárias. Vem das listas de presença do SAPL, que conferimos com as atas: batem.
Licença não é falta: os períodos de licença saem das Portarias da Câmara, revisadas uma a uma, com link em cada vereador.
Ausência justificada é a que a Câmara registrou como justificada.</dd></div>
<div><dt>Votos</dt><dd>A Câmara não registra o voto de cada vereador desde agosto de 2020. Só aparece o resultado geral,
como “aprovado por unanimidade”. Por isso não há como mostrar quem votou contra.</dd></div>
<div><dt>Salário</dt><dd>Não mostramos estimativas. Só entra no site o que tiver fonte oficial.</dd></div>
</dl>
<p class="nota">O código e os dados estão abertos no <a href="https://github.com/eltoncesar/radar-caceres">GitHub</a>,
com o <a href="https://github.com/eltoncesar/radar-caceres/blob/main/CONFERENCIA.md">relatório de conferência</a>.
Achou um erro? <a href="https://github.com/eltoncesar/radar-caceres/issues">Avise aqui</a>.</p>
</section>"""

    avisos = """<section class="secao avisos">
<div class="aviso"><strong>Por que não mostramos como cada vereador votou?</strong>
A Câmara não registra no sistema oficial o voto de cada vereador desde agosto de 2020.
Hoje só aparece o resultado geral, por exemplo “aprovado por unanimidade”.</div>
<div class="aviso"><strong>E a presença nas sessões?</strong>
Os registros batem com as atas, mas as licenças dos vereadores só aparecem nas Portarias da Câmara.
Vamos publicar a presença depois de cruzar cada licença, para não contar licença como falta.</div>
</section>"""

    script = f"""<script>
(function(){{
var SAPL="{sapl}",D=null,est={{q:"",g:""}},mostrando=5;
var MES=["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"];
function norm(t){{return (t||"").normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase().replace(/[^a-z0-9]+/g," ").trim();}}
function esc(t){{return String(t).replace(/[&<>"]/g,function(c){{return {{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}}[c];}});}}
function num(n){{return n.toLocaleString("pt-BR");}}
function data(d){{if(!d)return"";var p=d.split("-");return +p[2]+" "+MES[+p[1]-1]+" "+p[0];}}
function $(id){{return document.getElementById(id);}}
function filtrar(){{
  var q=norm(est.q),re=q?new RegExp("(^| )"+q.replace(/ /g," +")+"( |$)"):null;
  return D.propostas.filter(function(p){{return (!est.g||p.g===est.g)&&(!re||re.test(p._n));}});
}}
function ranking(contagem,n){{return Object.keys(contagem).sort(function(a,b){{return contagem[b]-contagem[a];}}).slice(0,n);}}
function avatar(id){{var v=D.vereadores[id];return v&&v.foto?'<img src="fotos/'+id+'.jpg" alt="" width="28" height="28">':'<span class="av"></span>';}}
function cartao(p){{
  var tags='<span class="tag g-'+p.g+'">'+esc(D.grupos[p.g])+'</span>'+p.s.slice(0,2).map(function(s){{return '<span class="tag">'+esc(D.assuntos[s])+'</span>';}}).join("");
  var autores=p.a.slice(0,3).map(function(a){{var v=D.vereadores[a];return '<a class="autor" href="vereador/'+v.slug+'.html">'+avatar(a)+esc(v.nome)+'</a>';}}).join("")+(p.a.length>3?'<span class="mais-aut">+'+(p.a.length-3)+'</span>':'');
  var ic=p.s.length?D.icones[p.s[0]]:D.icones["g_"+p.g];
  return '<li class="prop"><span class="ms ic-prop g-'+p.g+'" aria-hidden="true">'+ic+'</span><div class="prop-corpo"><p class="ementa" tabindex="0" title="Toque para ler tudo">'+esc(p.e||"Sem resumo no sistema oficial.")+'</p>'
    +'<p class="meta">'+tags+'<span>'+data(p.d)+' · '+esc(p.t)+' '+p.n+'</span></p>'
    +(p.x?'<p class="meta"><span class="sit s-'+p.x+'" title="Última movimentação oficial: '+esc(p.xs)+'"><span class="ms" aria-hidden="true">'+D.icones["x_"+p.x]+'</span>'+esc(p.xr)+'</span></p>':'')
    +'<div class="autores">'+autores+'</div><a class="link" href="'+SAPL+'/materia/'+p.i+'">Abrir na Câmara<span class="ms" aria-hidden="true">open_in_new</span><span class="sr"> (abre o site oficial)</span></a></div></li>';
}}
function barras(titulo,itens,max){{
  if(!itens.length)return"";
  return '<h3>'+titulo+'</h3><ol class="ranking">'+itens.map(function(x){{
    return '<li><span class="r-nome">'+x[0]+'</span><b>'+num(x[1])+'</b><i style="--w:'+Math.round(100*x[1]/max)+'%"></i></li>';}}).join("")+'</ol>';
}}
function desenhar(){{
  var achados=filtrar(),out=$("painel"),qv=est.q.trim();
  var porVer={{}},porAss={{}},porBairro={{}};
  achados.forEach(function(p){{p.a.forEach(function(a){{porVer[a]=(porVer[a]||0)+1;}});p.s.forEach(function(s){{porAss[s]=(porAss[s]||0)+1;}});p.b.forEach(function(b){{porBairro[b]=(porBairro[b]||0)+1;}});}});
  var onde=qv?'que citam <b>“'+esc(qv)+'”</b>':'para <b>a cidade inteira</b>';
  var grupo='';document.querySelectorAll(".aba").forEach(function(a){{a.setAttribute("aria-pressed",a.getAttribute("data-aba")===est.g?"true":"false");}});
  if(!achados.length){{out.innerHTML=grupo+'<p class="vazio">Nenhuma proposta '+(qv?'cita “'+esc(qv)+'”':'neste grupo')+'. Tente outro jeito de escrever o nome.</p>';ligar();return;}}
  var h=grupo+'<p class="grande"><b>'+num(achados.length)+'</b></p><p class="sub-grande">propostas '+onde+' até agora</p>';
  var ped=achados.filter(function(p){{return p.tn==="Indicação"||p.tn==="Requerimento";}}),resp=ped.filter(function(p){{return p.x==="respondido";}}).length,agu=ped.filter(function(p){{return p.x==="aguardando";}}).length;
  if(ped.length)h+='<div class="respostas"><p><b>'+num(resp)+'</b> de '+num(ped.length)+' pedidos já têm resposta escrita da Prefeitura'+(agu?' · <b>'+num(agu)+'</b> aguardando':'')+'.</p>'
    +'<i style="--w:'+Math.round(100*resp/ped.length)+'%"></i><p class="sub">Resposta recebida não quer dizer que o problema foi resolvido: abra o pedido na Câmara para ler a resposta.</p></div>';
  var tv=ranking(porVer,5);
  h+=barras("Quem mais propôs",tv.map(function(a){{var v=D.vereadores[a];return [avatar(a)+esc(v.nome)+(v.partido?' <small>· '+esc(v.partido)+'</small>':''),porVer[a]];}}),porVer[tv[0]]||1);
  var ta=ranking(porAss,5);
  h+=barras("O que mais pedem",ta.map(function(s){{return [esc(D.assuntos[s]),porAss[s]];}}),porAss[ta[0]]||1);
  if(!qv){{var tb=ranking(porBairro,5);h+=barras("Bairros mais citados",tb.map(function(b){{return ['<button type="button" class="link" data-q="'+esc(D.bairros[b])+'">'+esc(D.bairros[b])+'</button>',porBairro[b]];}}),porBairro[tb[0]]||1);}}
  h+='<h3>'+(qv?'Propostas que citam esse lugar':'As propostas mais recentes')+'</h3><ol class="props">'+achados.slice(0,mostrando).map(cartao).join("")+'</ol>';
  if(achados.length>mostrando)h+='<button type="button" class="botao" id="mais-props">Mostrar mais '+Math.min(10,achados.length-mostrando)+' de '+num(achados.length-mostrando)+'</button>';
  out.innerHTML=h;ligar();
}}
function ligar(){{
  document.querySelectorAll("[data-q]").forEach(function(b){{b.onclick=function(){{ir(b.getAttribute("data-q"),"");}};}});
  document.querySelectorAll("[data-g]").forEach(function(b){{b.onclick=function(){{ir("",b.getAttribute("data-g"));}};}});
  var m=$("mais-props");if(m)m.onclick=function(){{mostrando+=10;desenhar();}};
  document.querySelectorAll(".aba").forEach(function(a){{a.onclick=function(){{est.g=a.getAttribute("data-aba");mostrando=5;salvar();desenhar();}};}});
  document.querySelectorAll(".ementa").forEach(function(e){{e.onclick=function(){{e.classList.toggle("aberta");}};e.onkeydown=function(k){{if(k.key==="Enter")e.classList.toggle("aberta");}};}});
}}
function salvar(){{var h=[];if(est.q)h.push("q="+encodeURIComponent(est.q));if(est.g)h.push("g="+est.g);try{{history.replaceState(null,"",h.length?"#"+h.join("&"):location.pathname);}}catch(e){{}}}}
function ir(q,g){{est.q=q;est.g=g;$("q").value=q;mostrando=5;salvar();desenhar();$("busca").scrollIntoView({{behavior:"smooth"}});}}
function lerHash(){{var h=location.hash.slice(1);if(!h)return;if(h.indexOf("=")<0){{est.q=decodeURIComponent(h);return;}}h.split("&").forEach(function(x){{var p=x.split("=");if(p[0]==="q")est.q=decodeURIComponent(p[1]||"");if(p[0]==="g")est.g=p[1]||"";}});}}
$("q").addEventListener("input",function(){{est.q=$("q").value;mostrando=5;salvar();if(D)desenhar();}});
document.querySelectorAll("[data-q],[data-g]").forEach(function(){{}});
var mr=$("mais-reps");if(mr)mr.onclick=function(){{document.querySelectorAll(".rep.oculto").forEach(function(x,i){{if(i<6)x.classList.remove("oculto");}});var r=document.querySelectorAll(".rep.oculto").length;if(r)mr.textContent="Mostrar mais ruas ("+r+" na fila)";else mr.remove();}};
fetch("dados.json").then(function(r){{return r.json();}}).then(function(d){{
  d.propostas.forEach(function(p){{p._n=norm(p.e);}});D=d;lerHash();$("q").value=est.q;desenhar();
  if(location.hash)$("busca").scrollIntoView();
}}).catch(function(){{$("painel").innerHTML='<p class="vazio">Não foi possível carregar as propostas. Recarregue a página.</p>';}});
ligar();
// Números que sobem e seções que entram (respeita quem prefere menos movimento)
var calmo=window.matchMedia&&matchMedia("(prefers-reduced-motion: reduce)").matches;
if(!calmo&&"IntersectionObserver" in window){{
  var ob=new IntersectionObserver(function(es){{es.forEach(function(e){{if(e.isIntersecting){{e.target.classList.add("visivel");ob.unobserve(e.target);}}}});}},{{rootMargin:"0px 0px -10% 0px"}});
  document.querySelectorAll(".entra").forEach(function(x){{ob.observe(x);}});
  document.querySelectorAll("[data-conta]").forEach(function(b){{var fim=+b.getAttribute("data-conta"),t0=null,dur=1100;
    function passo(t){{if(!t0)t0=t;var k=Math.min(1,(t-t0)/dur);k=1-Math.pow(1-k,3);b.textContent=Math.round(fim*k).toLocaleString("pt-BR");if(k<1)requestAnimationFrame(passo);}}
    requestAnimationFrame(passo);}});
}}else document.querySelectorAll(".entra").forEach(function(x){{x.classList.add("visivel");}});
setTimeout(function(){{document.querySelectorAll(".entra").forEach(function(x){{x.classList.add("visivel");}});}},4000);
// Crachás
var lista=$("crachas"),itens=[].slice.call(lista.children);
function crachas(){{
  var n=norm($("f-nome").value),pt=$("f-partido").value,o=$("f-ordem").value,vis=0;
  itens.sort(function(a,b){{if(o==="nome")return (b.dataset.titular-a.dataset.titular)||a.dataset.nome.localeCompare(b.dataset.nome,"pt");return (+b.dataset[o])-(+a.dataset[o])||a.dataset.nome.localeCompare(b.dataset.nome,"pt");}});
  itens.forEach(function(li){{var ok=(!n||norm(li.dataset.nome).indexOf(n)>=0)&&(!pt||li.dataset.partido===pt);li.hidden=!ok;if(ok)vis++;lista.appendChild(li);}});
  $("f-conta").textContent="Mostrando "+vis+" de "+itens.length+".";
}}
["f-nome","f-partido","f-ordem"].forEach(function(id){{$(id).addEventListener("input",crachas);}});crachas();
}})();
</script>"""
    return topo + busca + repete + trabalho + vereadores_html + fontes + script


def escrever_dados(caminho, vereadores, coleta):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados_json(vereadores, coleta), f, ensure_ascii=False, separators=(",", ":"))
