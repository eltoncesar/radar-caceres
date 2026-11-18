"""Dados da página inicial (propostas, lugares, situação) e funções de apoio usadas pela pagina_v2."""
import collections
import json

from assuntos import ASSUNTOS, assuntos
from classificar import GRUPOS, ORDEM as ORDEM_GRUPOS
from locais import Rotulos, bairros, ruas
import situacao as sit
from resumo import resumo

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
                    **({"rs": resumo(p["ementa"])} if resumo(p["ementa"]) != p["ementa"] else {}),
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


# Explicação em linguagem simples de cada tipo (mesma do glossário em "Como funciona").
EXPLICA_TIPO = {}


def dados_json(vereadores, coleta):
    lista, rr, rb = montar(vereadores)
    return {
        "coleta": coleta,
        "grupos": {g: GRUPOS[g][0] for g in ORDEM_GRUPOS},
        "assuntos": NOME_ASSUNTO,
        "explica_tipo": EXPLICA_TIPO,
        "explica_situacao": sit.EXPLICA,
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


def bloco_discursos(v, esc, data_br):
    ds = v.get("discursos") or []
    if not ds:
        return """<section class="presenca" id="tribuna"><h2>Na tribuna</h2>
<p class="sub">Nenhum discurso registrado no sistema da Câmara nesta legislatura.</p></section>"""
    itens = "".join(
        f'<li><a href="{esc(d["link"])}">{data_br(d["data"])}'
        f'{icone("play_circle") if d["video"] else ""}<span class="sr">{" (vídeo da sessão)" if d["video"] else " (página da sessão)"}</span></a></li>'
        for d in ds)
    return f"""<section class="presenca" id="tribuna"><h2>Na tribuna</h2>
<p class="pct"><b>{len(ds)}</b> <span>{"vez" if len(ds) == 1 else "vezes"} na lista de oradores das sessões</span></p>
<p class="sub">Cada data abre o vídeo da sessão inteira, quando a Câmara publicou o vídeo.</p>
<ul class="datas">{itens}</ul>
<p class="nota">Vem da lista de oradores que a Câmara registra no sistema. Algumas sessões não têm oradores registrados.</p></section>"""


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


