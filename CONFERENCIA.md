# Conferência dos dados (Passo 5)

Feita em 17/11/2026, antes de publicar o site.

## O que foi conferido e bate

| Conferência | Como | Resultado |
|---|---|---|
| Total de propostas de cada vereador | Site comparado com a busca por autor da API do SAPL | **21 de 21 batem** |
| Propostas uma a uma | 45 propostas sorteadas, pelo menos uma de cada vereador, comparadas com a página pública de cada matéria no SAPL e com a aba de autoria (`conferencia/conferir_amostra.py`) | **45 de 45 batem** em tipo, número, ano, data, resumo e autores |
| Presença registrada no SAPL | Lista de presentes das 10 sessões ordinárias que têm ata publicada no SAPL comparada com a lista de abertura do SAPL | **10 de 10 iguais** |
| Situação de cada proposta (resposta da Prefeitura, virou lei) | Última movimentação de 12 propostas sorteadas comparada com o endereço `ultima_tramitacao` do SAPL | **12 de 12 batem** |
| Grupos de propostas | Leitura de 12 propostas sorteadas de cada grupo | Todas no grupo que a regra declara |

## O que não bate, e por quê

1. **Datas de mandato dos suplentes no SAPL estão erradas.** Exemplos:
   - Judson Prata aparece com mandato até 22/09/2026, mas a Câmara noticiou o fim do exercício dele quando Clóvis Salvador voltou, em 20/04/2026.
   - Wesley Lopes aparece com mandato até 2028, mas ele assumiu a vaga de Rubens Macedo, licenciado, e Rubens voltou em julho de 2026.

   Por isso o site **não pode** usar essas datas para calcular presença.

2. **As licenças não aparecem no SAPL, mas foram noticiadas pela Câmara.** As ausências longas encontradas nos dados são licenças, todas confirmadas no site oficial (caceres.mt.leg.br):

| Titular afastado | Motivo (segundo a Câmara) | Quem assumiu |
|---|---|---|
| Valdeníria | Assumiu cadeira na Assembleia Legislativa (jul/2025) | Alex Leal, posse em 10/07/2025 |
| Isaías Bezerra | Licença de saúde (ago/2025) | Celso Silva, posse em 22/08/2025 |
| Rubens Macedo | Secretário municipal, licença de 121 dias e depois de 174 dias | Wesley Lopes, posse em 12/09/2025 |
| Magaly | Secretária de Assistência Social, cerca de 7 meses; voltou em 22/04/2026 | Clóvis Salvador; depois Eliel da Rocha e Judson Prata, enquanto Clóvis se tratava |
| Jorge Augusto | Licença médica para cirurgia (fim de mar/2026); voltou em 22/04/2026 | — |

   Contar essas sessões como falta seria injusto. É exatamente o cuidado "dado ausente não é falta" do manual.

3. **Atas:** só 20 das 144 sessões da legislatura têm ata no SAPL, e só 10 delas são de sessões ordinárias. A conferência de presença com as atas cobre apenas fev–abr/2025.

## O que é estimativa ou não foi confirmado

- **Grupos e assuntos** são definidos por uma regra automática a partir do tipo e do resumo. Podem errar em casos raros, e o site diz isso.
- **A busca por bairro** só encontra pedidos cujo resumo cita o lugar.
- **Voto de cada vereador:** não existe no SAPL desde agosto de 2020. Não há o que conferir.
- **Presença:** os registros do SAPL batem com as atas, mas só vamos publicar depois de montar a tabela de licenças com as datas exatas de início e fim, a partir de fontes oficiais (atos da Mesa, termos de posse, notícias da Câmara). Até lá, o site não mostra presença.

## Falta você fazer

Abrir a ficha oficial de dois ou três vereadores no SAPL (o link está na página de
cada um no site) e comparar com o que o site mostra.
