"""Situação de cada proposta, a partir da última movimentação (tramitação) no SAPL.

Para pedidos (indicações e requerimentos), a Câmara registra quando manda o
ofício à Prefeitura ("Aguardando Ofício Resposta") e quando recebe a resposta
("Recebido Ofício Resposta"). Resposta recebida não quer dizer que o problema
foi resolvido: quer dizer que a Prefeitura respondeu por escrito.

Para projetos, o que importa é se viraram norma (sancionada ou promulgada).
"""

RESPONDIDO = "respondido"
AGUARDANDO = "aguardando"
VIROU_NORMA = "virou_norma"
NAO_AVANCOU = "nao_avancou"
TRAMITANDO = "tramitando"
ENCERRADO = "encerrado"

ROTULO = {
    RESPONDIDO: "Prefeitura respondeu",
    AGUARDANDO: "Aguardando resposta",
    VIROU_NORMA: "Virou lei",
    NAO_AVANCOU: "Não avançou",
    TRAMITANDO: "Em tramitação",
    ENCERRADO: "Encerrado sem resposta",
}
ICONE = {RESPONDIDO: "mark_email_read", AGUARDANDO: "schedule", VIROU_NORMA: "gavel",
         NAO_AVANCOU: "block", TRAMITANDO: "pending", ENCERRADO: "block"}

TIPOS_PEDIDO = {"Indicação", "Requerimento"}
TIPOS_PROJETO = {"Projeto de Lei", "Projeto de Lei Complementar", "Projeto de Resolução",
                 "Proposta de Emenda à Lei Orgânica", "Projeto de Decreto Legislativo"}

NORMA = {"Norma Sancionada", "Norma Promulgada", "Norma Sancionada com Veto Parcial",
         "Norma Promulgada com Veto Parcial"}
FIM_SEM_EXITO = {"Proposição Arquivada", "Proposição Prejudicada", "Proposição Retirada pelo Autor/Líder do Governo",
                 "Proposição Reprovada em 1º Turno", "Proposição Reprovada em 2º Turno",
                 "Proposição Reprovada em Turno Único", "Proposição Reprovada pela Mesa Diretora", "Veto Total Mantido"}


def ultimas(tramitacoes, status):
    """{matéria: (data, texto do status)} da movimentação mais recente de cada matéria."""
    ult = {}
    for t in sorted(tramitacoes, key=lambda t: (t["data_tramitacao"] or "", t.get("timestamp") or "", t["id"])):
        ult[t["materia"]] = (t["data_tramitacao"], status.get(t["status"], ""))
    return ult


def situacao(tipo, ultimo_status):
    """Devolve a chave da situação, ou None quando não se aplica (homenagens, moções)."""
    if tipo in TIPOS_PEDIDO:
        if ultimo_status == "Recebido Ofício Resposta da Propositura":
            return RESPONDIDO
        if ultimo_status == "Aguardando Ofício Resposta da Propositura":
            return AGUARDANDO
        if ultimo_status in FIM_SEM_EXITO:
            return ENCERRADO
        return TRAMITANDO
    if tipo in TIPOS_PROJETO:
        if ultimo_status in NORMA:
            return VIROU_NORMA
        if ultimo_status in FIM_SEM_EXITO:
            return NAO_AVANCOU
        return TRAMITANDO
    return None
