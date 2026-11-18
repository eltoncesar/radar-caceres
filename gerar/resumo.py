"""Resumo legível: pula a fórmula regimental do começo da ementa.

Muitas ementas começam com "O Vereador que abaixo subscreve propõe à nobre Mesa,
consultado o augusto e soberano Plenário, na forma regimental, ...". Para quem
lê no celular, o pedido em si fica escondido. Quando a ementa começa com essa
fórmula, o resumo começa no verbo do pedido ("indica", "requer", "seja
encaminhado", "moção de" ...), marcado com "…".

Só muda a exibição. O texto oficial completo continua a um toque e no link
para a Câmara.
"""
import re

COMECA_COM_FORMULA = re.compile(
    r"^(?:ementa\s*:\s*)?(?:assunto\s*:|(?:o|a|os|as)\s+ver(?:eador|eadora|eadores|eadoras|\.|:)|vereador)", re.I)
PEDIDO = re.compile(
    r"\b(indic[ao]|indicar|requerer|requer|requeiro|encaminha|solicit[ao]|solicitar|propor|prop[õo]e"
    r"|sejam?\s+(?:encaminhad|consignad|registrad|enviad|oficiad|aprovad)\w*"
    r"|encaminhar|manifestar|mo[çc][ãa]o\s+de)\b", re.I)
# Verbos de tramitação interna, que ainda fazem parte da fórmula.
INTERNO = re.compile(r"^\s*(?:(?:a|à)\s+nobre\s+mesa|ap[óo]s\s+tramita|nos\s+termos|na\s+forma|ao\s+plen)", re.I)
LIMITE = 320


def resumo(ementa):
    texto = re.sub(r"\s+", " ", ementa or "").strip().strip("“”\"' ")
    if not COMECA_COM_FORMULA.match(texto):
        return texto
    for m in PEDIDO.finditer(texto):
        if m.start() > LIMITE:
            break
        if m.start() == 0 or INTERNO.match(texto[m.end():]):
            continue
        verbo = m.group(0)
        if verbo.isupper():
            verbo = verbo.capitalize()
        resto = verbo[:1].upper() + verbo[1:] + texto[m.end():]
        return "…" + resto if len(resto) >= 25 else texto
    return texto
