"""Encontra ruas e bairros citados no resumo (ementa) de cada pedido.

É uma leitura automática do texto: serve para agrupar pedidos repetidos no
mesmo lugar. Pode falhar quando o resumo escreve o nome de um jeito diferente.
Cada lugar tem uma chave sem acento (para agrupar) e um rótulo com a grafia
mais comum nos próprios pedidos (para mostrar).
"""
import collections
import re
import unicodedata

L = r"[a-zà-ÿ0-9'ºª]"
TIPOS_VIA = r"(rua|r\.|avenida|av\.?|travessa|tv\.|alameda|estrada|rodovia|passagem)"
TIPOS_BAIRRO = r"(bairros?|jardim|jd\.?|vila|loteamento|residencial|conjunto|distrito|comunidade|assentamento|cohab)"
FIM = (r"(?=\s*(?:,|;|\.(?:\s|$)|:|\(|\)|–|—|-\s|\bn[ºo°]\.?\s|\bnúmero\b|\bbairro\b|\bnas?\b|\bnos?\b|\bem\b|"
       r"\bentre\b|\besquina\b|\bpróximo\b|\bproximo\b|\bdesde\b|\baté\b|\bcom\b|\bque\b|\bpara\b|\bjunto\b|"
       r"\bsentido\b|\blocalizad|\bsituad|\bdo município\b|\bdeste município\b|\bem cáceres\b|\bde cáceres\b|$))")
NOME = rf"((?:{L}[{L[1:-1]}\.]*\s?){{1,7}}?)"
RE_VIA = re.compile(rf"\b{TIPOS_VIA}\s+{NOME}{FIM}")
RE_BAIRRO = re.compile(rf"\b{TIPOS_BAIRRO}\s*:?\s+{NOME}{FIM}")

DESCARTAR = {"", "publica", "publicas", "municipal", "principal", "de acesso", "acesso", "vicinal", "vicinais",
             "rural", "urbana", "urbano", "localizada", "localizado", "situada", "s", "dos", "das", "do", "da", "de"}
GENERICOS = {"cidade", "municipio", "caceres", "regiao", "rural", "urbano", "zona", "mesmo", "mesma", "referido",
             "referida", "citado", "citada", "supracitado", "acima"}
PEQUENAS = {"da", "do", "de", "das", "dos", "e"}


NUMEROS = {"7 de setembro": "sete de setembro", "13 de junho": "treze de junho", "15 de novembro": "quinze de novembro"}


def chave(texto):
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    for numero, extenso in NUMEROS.items():
        t = t.replace(numero, extenso)
    return t


def _limpar(nome):
    nome = re.sub(r"[\.'\s]+$", "", nome.strip())
    nome = re.sub(r"^(?:de|do|da|dos|das)\s+(?=(?:vila|jardim|bairro|santo|nova|são|sao)\b)", "", nome)
    nome = re.sub(r"\s+(?:em|no|na|do|da|de|e|dos|das)$", "", nome)
    return nome.strip()


def _titulo(nome):
    def palavra(p):
        if p in PEQUENAS:
            return p
        if re.fullmatch(r"[ivx]+", p):
            return p.upper()
        return p[:1].upper() + p[1:]
    return " ".join(palavra(p) for p in nome.split())


def _achar(regex, ementa, montar):
    texto = re.sub(r"[“”\"]", " ", (ementa or "").lower())
    texto = re.sub(r"\s+", " ", texto)
    achados = {}
    for m in regex.finditer(texto):
        tipo = m.group(1).rstrip(".:")
        nome = _limpar(m.group(2))
        k = chave(nome)
        if k in DESCARTAR or not k or k.split()[0] in GENERICOS or len(k) < 3 or k.startswith(("do ", "de ", "da ")):
            continue
        rotulo = montar(tipo, nome)
        achados.setdefault(chave(rotulo), rotulo)
    return achados


def _via(tipo, nome):
    tipo = {"r": "rua", "av": "avenida", "tv": "travessa"}.get(tipo, tipo)
    return f"{_titulo(tipo)} {_titulo(nome)}"


def _bairro(tipo, nome):
    if tipo in ("jardim", "jd", "vila", "residencial", "conjunto", "cohab") and not nome.startswith(tipo):
        nome = f"{'jardim' if tipo == 'jd' else tipo} {nome}"
    return _titulo(nome)


def ruas(ementa):
    """{chave: rótulo} das ruas citadas, como 'Rua Sete de Setembro'."""
    return _achar(RE_VIA, ementa, _via)


def bairros(ementa):
    """{chave: rótulo} de bairros, distritos e comunidades, como 'Vila Irene'."""
    return _achar(RE_BAIRRO, ementa, _bairro)


class Rotulos:
    """Guarda a grafia mais comum de cada lugar para mostrar no site."""

    def __init__(self):
        self.contagem = collections.defaultdict(collections.Counter)

    def anotar(self, achados):
        for k, rotulo in achados.items():
            self.contagem[k][rotulo] += 1
        return list(achados)

    def rotulo(self, k):
        return self.contagem[k].most_common(1)[0][0]
