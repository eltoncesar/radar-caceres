"""Presença nas sessões ordinárias, descontando licenças.

Fonte: listas de presença do SAPL (abertura e Ordem do Dia; presente em qualquer
uma conta como presente), justificativas de ausência do SAPL e a tabela de
licenças montada a partir das Portarias (dados/licencas.json).

- Titular: contam as sessões fora dos períodos de licença.
- Suplente: contam as sessões dentro dos períodos de exercício. No dia da
  posse, a ausência não conta, porque a posse pode ser depois da sessão.
- Sessão sem nenhuma lista de presença registrada não conta para ninguém.
"""
import collections


def calcular(sessoes, tipos_sessao, presencas_listas, justificativas, mandatos, licencas, hoje):
    presentes = collections.defaultdict(set)
    for lista in presencas_listas:
        for p in lista:
            presentes[p["sessao_plenaria"]].add(p["parlamentar"])
    ordinarias = sorted((s for s in sessoes if s["data_inicio"] <= hoje and tipos_sessao.get(s["tipo"]) == "Ordinária"
                         and presentes[s["id"]]), key=lambda s: s["data_inicio"])
    justif = collections.defaultdict(set)
    for j in justificativas:
        justif[j["parlamentar"]].add(j["sessao_plenaria"])
    fora = collections.defaultdict(list)
    for item in licencas["licencas"]:
        fora[item["parlamentar"]].append(item)
    exercicio = {s["parlamentar"]: s for s in licencas["suplentes"]}

    resultado = {}
    for m in mandatos:
        pid = m["parlamentar"]
        if pid in exercicio:
            periodos = exercicio[pid]["periodos"]
            conta = [s for s in ordinarias if any(a <= s["data_inicio"] <= b for a, b in periodos)
                     and not (pid not in presentes[s["id"]] and any(s["data_inicio"] == a for a, _ in periodos))]
        else:
            conta = [s for s in ordinarias if not any(l["inicio"] <= s["data_inicio"] <= l["fim"] for l in fora[pid])]
        ausentes = [s for s in conta if pid not in presentes[s["id"]]]
        justificadas = [s for s in ausentes if s["id"] in justif[pid]]
        faltas = [s for s in ausentes if s["id"] not in justif[pid]]
        resultado[pid] = {
            "sessoes": len(conta),
            "presente": len(conta) - len(ausentes),
            "justificadas": [(s["id"], s["data_inicio"]) for s in justificadas],
            "faltas": [(s["id"], s["data_inicio"]) for s in faltas],
            "licencas": fora.get(pid, []),
            "exercicio": exercicio.get(pid),
        }
    return resultado
