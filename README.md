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

Os arquivos ficam em `dados/brutos/` e as fotos em `dados/fotos/`. Se a coleta
vier vazia, com linhas repetidas ou bem menor que a anterior, o script para sem
gravar nada. Precisa do Pillow (`pip install pillow`) para reduzir as fotos.

Para gerar o site na pasta `site/`:

```
python3 gerar/gerar_site.py
```

## Publicação automática

O robô em `.github/workflows/publicar.yml` roda toda madrugada (03h17 em Cáceres):
coleta os dados de novo, salva no repositório, gera o site e publica no GitHub
Pages. Se a coleta vier estranha, ele para com erro e o site continua com a última
versão boa. Também dá para rodar à mão em **Actions → Coletar e publicar → Run
workflow**. Quando o código muda na `main`, o site é gerado de novo com os dados
que já estão salvos.

Requisito: em **Settings → Pages → Source**, escolher **GitHub Actions**.

## Grupos de propostas

As propostas são separadas em cinco grupos: pedidos de melhoria, perguntas e
cobranças, homenagens, projetos de lei e regras, e outros. A regra está em
`gerar/classificar.py`, é a mesma para todos os vereadores e é explicada no site,
na página "Como funciona". Em nov/2026 só 5 das 2.580 propostas de vereadores
caíram em "Outros".

## Busca por bairro

A página `busca.html` procura o lugar digitado (bairro, rua, comunidade) no
resumo oficial dos pedidos de melhoria e das cobranças. Dentro do resultado, os
pedidos são agrupados por assunto (regra em `gerar/assuntos.py`), e o site mostra
quando o mesmo assunto volta mais de uma vez, com as datas e quem pediu. O site
avisa que pedido repetido não prova que a Prefeitura ignorou o problema.

## Conferência

Em 17/11/2026: totais de propostas dos 21 vereadores batem com o SAPL, 45 de 45
propostas sorteadas batem com as páginas oficiais, e a presença registrada no SAPL
bate com as 10 atas de sessões ordinárias disponíveis. Detalhes, divergências e
estimativas em [CONFERENCIA.md](CONFERENCIA.md).

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

1. **Há duas listas por sessão** (abertura e Ordem do Dia). Elas coincidem em
   75 das 84 sessões ordinárias. Regra adotada: o vereador conta como presente
   se aparecer em qualquer uma das duas.
2. **Licenças não estão registradas no SAPL.** As ausências longas (Rubens
   Macedo, Magaly, Isaías Bezerra, Valdeníria, Jorge Augusto) são licenças
   confirmadas nas Portarias da Câmara. A tabela de licenças fica em
   `dados/licencas.json` e é revisada à mão (ver CONFERENCIA.md).
3. **As datas de mandato dos suplentes parecem não bater** com o período em que
   eles ocuparam a cadeira.
4. Sessão sem presença registrada não conta como falta para ninguém.

## Regras do projeto

- Só dado oficial, com link para a fonte.
- A mesma régua para todos os vereadores.
- O que for estimativa é dito ao lado do número.
- Só contato público de gabinete.
- Encontrou um erro? Abra uma *issue* neste repositório.
