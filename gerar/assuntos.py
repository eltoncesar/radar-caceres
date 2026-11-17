"""Assuntos dos pedidos, para a busca por bairro e os problemas que se repetem.

Um pedido pode ter mais de um assunto. A regra procura palavras no resumo
(ementa), sem acento e sem diferença entre maiúsculas e minúsculas.
"""
import re
import unicodedata

ASSUNTOS = [
    ("iluminacao", "Iluminação pública", (r"ilumina", r"lampada", r"luminaria", r"\bpostes?\b", r"\bled\b")),
    ("asfalto", "Asfalto e buracos", (r"asfalt", r"paviment", r"buraco", r"recape", r"meio[ -]fio", r"\bsarjeta")),
    ("estrada", "Estradas de chão e pontes", (r"patrol", r"cascalh", r"terraplen", r"\bvicina", r"\bestradas?\b",
                                              r"\bpontes?\b", r"mata-burro", r"\bbueiro de estrada")),
    ("limpeza", "Limpeza e mato", (r"limpeza", r"\brocad", r"\bcapina", r"\bmato\b", r"\blixo", r"entulho",
                                   r"terreno baldio", r"coleta de residuo")),
    ("agua", "Água e esgoto", (r"\bagua\b", r"esgoto", r"hidrometro", r"vazamento", r"saneamento", r"fossa")),
    ("drenagem", "Drenagem e alagamento", (r"drenage", r"bueiro", r"boca de lobo", r"galeria", r"alagam",
                                           r"enxurrada", r"aguas pluviais")),
    ("transito", "Trânsito e sinalização", (r"sinaliza", r"quebra[ -]molas?", r"lombada", r"redutor",
                                             r"faixa de pedestre", r"semaforo", r"\btransito")),
    ("saude", "Saúde", (r"\bubs\b", r"posto de saude", r"unidade (basica )?de saude", r"\bsaude\b", r"medic",
                        r"ambulancia", r"\bsamu\b", r"hospital")),
    ("educacao", "Escolas e creches", (r"escola", r"creche", r"\bensino\b", r"educac")),
    ("lazer", "Praças, quadras e esporte", (r"\bpraca", r"\bquadra", r"academia", r"campo de futebol", r"\bparque")),
    ("arvores", "Poda e árvores", (r"\bpoda", r"arvore")),
    ("transporte", "Ônibus e transporte", (r"onibus", r"transporte (coletivo|publico|escolar)", r"ponto de parada")),
]
NOMES = {chave: nome for chave, nome, _ in ASSUNTOS}


def normalizar(texto):
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


# "com cópia à Secretaria Municipal de Saúde" não quer dizer que o pedido é sobre saúde.
SECRETARIA = re.compile(r"(secretari\w*|secretario\w*|pasta|orgao|autarquia)( municipal| especial| estadual)*"
                        r"( de| da| do)? \w+(( e| de| da| do| das| dos)? \w+){0,3}")


def assuntos(ementa):
    e = SECRETARIA.sub(" ", normalizar(ementa))
    return [chave for chave, _, padroes in ASSUNTOS if any(re.search(p, e) for p in padroes)]
