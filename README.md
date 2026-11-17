# Radar Cáceres

Site que mostra, só com dados oficiais, o que cada vereador de Cáceres-MT faz:
presença nas sessões e propostas apresentadas.

## De onde vêm os dados

Tudo vem da API pública do SAPL da Câmara Municipal:
<https://sapl.caceres.mt.leg.br/api/>. Não é preciso login.

Para coletar de novo:

```
python3 coleta/coletar.py
```

Os arquivos ficam em `dados/brutos/`. Se a coleta vier vazia ou bem menor que a
anterior, o script para sem gravar nada.

## O que existe e o que não existe (verificado em nov/2026)

| Dado | Situação |
|---|---|
| Vereadores e mandatos | Existe. 15 titulares e 6 suplentes na 20ª legislatura (2025–2028) |
| Sessões | Existe. Ordinárias, extraordinárias, solenes e itinerante |
| Propostas e autores | Existe. Indicações, requerimentos, moções, projetos etc. |
| Presença | Existe, com ressalvas (abaixo) |
| Justificativa de ausência | Existe, mas quase nunca é registrada |
| Como cada vereador votou | **Não existe.** O último voto nominal registrado é de agosto de 2020. Desde então só há o placar total |
| Atas | Poucas sessões têm ata no sistema. A maioria tem vídeo no YouTube |

## Ressalvas sobre presença

1. **Há duas listas por sessão** (abertura e Ordem do Dia), e elas raramente
   coincidem. Regra adotada: o vereador conta como presente se aparecer em
   qualquer uma das duas.
2. **Licenças não estão registradas.** Sequências longas de ausência coincidem
   com a posse de suplentes. Antes de publicar a presença, esses períodos
   precisam ser conferidos em uma fonte oficial (atos da Mesa, portarias).
3. **As datas de mandato dos suplentes parecem não bater** com o período em que
   eles ocuparam a cadeira.
4. Sessão sem presença registrada não conta como falta para ninguém.

## Regras do projeto

- Só dado oficial, com link para a fonte.
- A mesma régua para todos os vereadores.
- O que for estimativa é dito ao lado do número.
- Só contato público de gabinete.
- Encontrou um erro? Abra uma *issue* neste repositório.
