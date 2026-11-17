"""Regra única que separa as propostas em grupos simples.

A mesma regra vale para todos os vereadores. Ela olha o tipo oficial da
proposta e algumas palavras do resumo (ementa). Está explicada em linguagem
simples na página "Como funciona" do site (ver REGRA_EXPLICADA).
"""
import re
import unicodedata

MELHORIA = "melhoria"
COBRANCA = "cobranca"
HOMENAGEM = "homenagem"
LEI = "lei"
OUTROS = "outros"

GRUPOS = {
    MELHORIA: ("Pedidos de melhoria", "Pedidos para a Prefeitura ou outro órgão fazer algo: obra, conserto, serviço, equipamento."),
    COBRANCA: ("Perguntas e cobranças", "Pedidos de informação, de documentos ou de explicação sobre o que o poder público está fazendo."),
    HOMENAGEM: ("Homenagens", "Aplausos, pesar, títulos de cidadão, diplomas, nomes de rua e datas comemorativas."),
    LEI: ("Projetos de lei e regras", "Propostas que criam ou mudam leis do município ou regras da Câmara."),
    OUTROS: ("Outros", "Tudo que não se encaixa nos grupos acima, como pedidos internos da Câmara."),
}
ORDEM = [MELHORIA, COBRANCA, HOMENAGEM, LEI, OUTROS]

REGRA_EXPLICADA = [
    ("Pedidos de melhoria", "Todas as indicações."),
    ("Perguntas e cobranças", "Os requerimentos, que são pedidos formais de informação, documento ou "
     "providência (inclusive pedidos de CPI), e as moções de apelo ou repúdio."),
    ("Homenagens", "Moções de aplauso, pesar ou solidariedade; projetos que dão título, diploma ou honraria; "
     "projetos de lei que dão nome a rua ou lugar ou criam dia, semana ou mês comemorativo; "
     "requerimentos de aplauso, pesar ou sessão solene."),
    ("Projetos de lei e regras", "Os demais projetos de lei, de lei complementar, de resolução, "
     "emendas e propostas de mudança na Lei Orgânica."),
    ("Outros", "O que sobrar, como requerimentos sobre a pauta, a tribuna ou licenças, "
     "e a votação das contas da Prefeitura."),
]


def _normalizar(texto):
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t)


def _tem(texto, *padroes):
    return any(re.search(p, texto) for p in padroes)


HONRARIA = (r"titulo", r"diploma", r"merito", r"cidada", r"honra", r"comenda", r"medalha", r"homenag")
REQ_HOMENAGEM = (r"aplauso", r"congratula", r"\bpesar\b", r"voto de louvor", r"sessao solene", r"parabeniza")
REQ_INTERNO = (r"inclus\w* (na|em|de) pauta", r"regime de urgencia", r"tribuna livre", r"\blicenca\b",
               r"submetida ao plenario")
COMEMORATIVA = (r"\bdenomin", r"da nome", r"\bnome de\b", r"institui (o|a) (dia|semana|mes|data)",
                r"calendario oficial", r"\bdia municipal", r"semana municipal", r"mes municipal",
                r"data comemorativa")
TIPOS_LEI = ("Projeto de Lei", "Projeto de Lei Complementar", "Projeto de Resolução",
             "Proposta de Emenda à Lei Orgânica", "Emenda Parlamentar")


def classificar(tipo, ementa):
    """Devolve o grupo de uma proposta a partir do tipo oficial e da ementa."""
    e = _normalizar(ementa)
    if tipo == "Indicação":
        return MELHORIA
    if tipo == "Moção":
        return COBRANCA if _tem(e, r"apelo", r"repudio") else HOMENAGEM
    if tipo == "Projeto de Decreto Legislativo":
        return HOMENAGEM if _tem(e, *HONRARIA) else OUTROS
    if tipo == "Requerimento":
        if _tem(e, *REQ_HOMENAGEM):
            return HOMENAGEM
        if _tem(e, *REQ_INTERNO):
            return OUTROS
        return COBRANCA
    if tipo in TIPOS_LEI:
        if tipo == "Projeto de Lei" and _tem(e, *COMEMORATIVA):
            return HOMENAGEM
        return LEI
    return OUTROS
