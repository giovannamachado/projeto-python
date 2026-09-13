# Robô Coletor de Celulares

Projeto final da disciplina. Um `RoboColetor` recebe um pedido de coleta,
navega pela grade de um laboratório de testes de dispositivos móveis, usa o
sistema de sucção para recolher cada protótipo, deposita tudo numa bandeja e
avisa a bancada de testes quando o lote está pronto para retirada. Só depois
que a equipe aprova o lote o robô aceita um pedido novo.

Continuação direta do código do fim do curso: mesma classe `Robo` (herdada de
`robo_base.py`, fornecido), mesmo modelo de features, mesma suíte `pytest`,
aplicados a um domínio novo.

## Setup

Só é preciso Python 3 e `pytest`; o resto é biblioteca padrão.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Como rodar

### Testes

Na raiz do projeto (o `pythonpath = ["src"]` do `pyproject.toml` já resolve o
import do pacote, não é preciso instalar nada):

```bash
pytest -v
```

### CLI

```bash
python main.py
```

O menu permite listar o pedido carregado, processar o pedido, ver o estado da
bandeja, aprovar ou rejeitar a retirada, desfazer a última coleta, consultar a
trilha de auditoria e gravá-la em JSON.

Os arquivos de entrada podem ser trocados por `argparse`:

```bash
python main.py --config dados/config_robo_quarentena.json \
               --pedido dados/pedido_coleta_fragil.json
```

`main.py` existe porque o `pythonpath` do `pyproject.toml` vale só para o
`pytest`: ele acrescenta `src/` ao `sys.path` e chama `celular_robo.cli.main`.
Quem preferir pode rodar `PYTHONPATH=src python -m celular_robo.cli`, dá no
mesmo.

## Arquivos de dados

| Arquivo | Para que serve |
|---|---|
| `dados/config_robo_exemplo.json` | Configuração do robô: tipo, rota, área. |
| `dados/config_robo_quarentena.json` | Mesma coisa, mas na área de quarentena com dupla conferência. |
| `dados/pedido_coleta_exemplo.json` | Pedido válido para o robô da configuração padrão. |
| `dados/pedido_coleta_fragil.json` | Pedido com itens frágeis — só roda com `dupla_conferencia`. |
| `dados/pedido_coleta_conflito.json` | Pedido que mistura `fragil` e `urgente`; existe para mostrar a recusa. |
| `dados/lote_testes.json` | Inventário do lote: codinome → unidades disponíveis. |

## Decisões de projeto

### A bandeja é uma classe própria

`Bandeja` (em `robo.py`) tem o seu próprio `__len__`, que devolve quantas
unidades já foram coletadas. Preferi isso a um `dict` solto dentro do
`RoboColetor` porque a invariante de quantidade (nunca negativa, nunca acima
do pedido) fica concentrada num lugar só, dentro do descriptor
`QuantidadeValida` de `ItemBandeja`.

Como consequência, `RoboColetor` **não** redefine `__len__`: continua valendo o
`__len__` herdado de `Robo`, que é o tamanho da trajetória. Quem quer o tamanho
da bandeja escreve `len(robo.bandeja)`, que é mais explícito do que fazer o
mesmo `len()` significar duas coisas diferentes dependendo da classe.

### Qual exceção recusa o quê

* **`fragil=True` e `urgente=True` no mesmo item → `PedidoInvalido`.** O item se
  contradiz sozinho: exigiria `dupla_conferencia` por ser frágil e `direta` por
  ser urgente, sem que exista robô nenhum envolvido. É um defeito do conteúdo do
  pedido, não de uma combinação de configuração. (`validar_item`, em
  `modelo_features.py`.)
* **Um item frágil num robô com rota direta → `ConfiguracaoInvalida`.** Aqui sim
  o problema é a combinação: o pedido está correto, o robô está correto, os dois
  juntos é que não funcionam. É o `requires` do modelo de features
  (`validar_pedido_para_rota`, chamado por `RoboColetor.carregar_pedido`).
* **Pedido com um item frágil e outro urgente → `PedidoInvalido`, pedido inteiro
  recusado.** `robo.estrategia` é única por robô, então nenhuma configuração
  atende os dois. Recuso o pedido inteiro antes de processar qualquer item, em
  vez de aceitar metade — meia coleta deixaria a bandeja num estado que nunca
  fica completa, e o robô nunca sairia de `ModoColetando`. A checagem acontece
  ao validar o **pedido** (`validar_pedido`), não em `validar_configuracao`, que
  só enxerga o JSON do robô.
* **Pedido com itens mistos, um deles inválido → rejeita o pedido inteiro.**
  Mesma razão: atomicidade. O pedido é a unidade de trabalho, e um lote
  parcialmente coletado é pior de auditar do que um lote recusado com o motivo
  registrado. O primeiro problema encontrado interrompe a validação, e nada é
  coletado (`test_pedido_misto_e_recusado_inteiro`).

Os três casos são `ErroColeta`, então quem chama pode tratar tudo junto com um
`except ErroColeta` ou separar por subclasse.

### De onde vem o lote

O JSON do pedido só traz o *nome* do lote. A relação codinome → unidades
disponíveis fica em `dados/lote_testes.json`, lida por
`persistencia.carregar_lote()`. Escolhi um arquivo em vez de um `dict` no
módulo porque o inventário é dado, não código: muda a cada lote novo, e do
jeito que está dá para rodar a CLI contra outro lote sem editar nada em `src/`.

`montar_pedido_de_json` carrega o inventário por conta própria quando não
recebe um, e os testes passam o deles pela fixture `estoque` — assim a suíte
não depende do conteúdo do arquivo.

### O `dados/pedido_coleta_exemplo.json` é diferente do exemplo do enunciado

O exemplo da Seção 2.6 tem um item urgente e um item frágil no mesmo pedido, o
que é exatamente o conflito que a Seção 2.4 manda recusar. Entendi aquele
trecho como demonstração do **formato** do JSON, não de um pedido válido:
copiei-o para `dados/pedido_coleta_conflito.json`, que serve para ver a recusa
acontecendo, e deixei em `pedido_coleta_exemplo.json` um pedido que roda de
ponta a ponta com a configuração de exemplo.

### Um módulo a mais: `pedido.py`

A estrutura sugerida no enunciado foi mantida; só acrescentei
`src/celular_robo/pedido.py`, com `ItemPedido` e `Pedido`. O pedido é o dado
central do projeto e aparece em quase todos os outros módulos — colocá-lo em
`persistencia.py` misturaria a forma do dado com a leitura de arquivo, e em
`modelo_features.py` misturaria o dado com as regras sobre ele. As **regras**
continuam todas em `modelo_features.py`, que é onde o modelo de features mora.

### Navegação: busca em largura

`RotaColeta._caminho_ate` faz uma busca em largura na grade (só
`collections.deque`, sem dependência externa) e devolve o menor caminho livre
até a prateleira; `navegar_ate` percorre esse caminho com `girar_ate`/`avancar`,
os mesmos métodos de `Robo`. Isso é o que torna a área de quarentena
interessante: o corredor bloqueado é contornado de verdade, e um destino que
ficasse isolado levanta `PedidoInvalido` em vez de o robô ficar preso batendo
na parede.

A diferença entre as duas rotas está na coleta, não no trajeto:
`RotaComDuplaConferencia` revalida a posição do item antes da sucção e de novo
antes de depositar (dois eventos `item_conferido` por item), e o `mover()` dela
só avança com o sensor confirmando o caminho livre.

### Descriptors levantam `ValueError`, não `ErroColeta`

`QuantidadeValida` segue o mesmo contrato de `Coordenada` e `Percentual`
(`robo_base.py`, fornecido): violação de invariante de atributo é `ValueError`/
`TypeError`. `ErroColeta` e suas subclasses ficam para os erros de domínio —
pedido, configuração —, que é o que a CLI captura e mostra ao usuário.

### Observer, State e a volta atrás

Quem troca o modo do robô é a `EquipeDeTestes`, reagindo a `"bandeja_pronta"` —
o modo não decide sozinho que a bandeja encheu. É o mesmo caminho do
`MonitorBateria` de `modos_base.py` trocando para `ModoCarregando`.

Duas consequências que vieram junto:

* **Rejeição** devolve o robô para `ModoColetando` com a bandeja intacta. Os
  itens já coletados continuam lá, e a rejeição vira uma linha na auditoria —
  não há reprocessamento automático.
* **Desfazer** uma coleta emite `"bandeja_reaberta"`; a equipe cancela a espera
  e o robô volta a `ModoColetando`, já que o lote deixou de estar completo.

`criar_robo_configurado` já pendura `RegistroAuditoria` e `EquipeDeTestes` no
robô (acessíveis como `robo.auditoria` e `robo.equipe`). Quem quiser o robô
"pelado" passa `com_observadores=False`.

### Dois imports locais, de propósito

`modelo_features.py` importa `robo.py` para que `RoboColetor`/
`RoboTransportador` já estejam em `Robo._registro` quando `TIPOS_VALIDOS` é
derivado. Por isso `robo.py` importa `validar_pedido_para_rota` **dentro** de
`carregar_pedido`, e `observadores.py` importa `criar_robo_configurado`
**dentro** de `DespachanteTransporte.atualizar` — nos dois casos o import no
topo fecharia um ciclo. Os dois pontos estão comentados no código.

## Mapeamento para os conteúdos da disciplina

| Mecanismo | Onde está |
|---|---|
| Herança e fundamentos de OO | `robo.py` — `RoboColetor(Robo)`, `RoboTransportador(Robo)` |
| Descriptors | `robo.py` — `QuantidadeValida` (usado em `ItemBandeja.coletada`); `Coordenada` herdada de `robo_base.py` |
| Métodos especiais | `Bandeja.__len__`/`__iter__`/`__contains__`/`__str__`; `Pedido.__len__`/`__iter__`/`__getitem__`; `__repr__`/`__str__` em robôs, rotas, modos e comandos |
| Metaprogramação — registro de robôs | `Robo.__init_subclass__` (fornecido) alimentando `Robo._registro`; `TIPOS_VALIDOS = set(Robo._registro)` em `modelo_features.py` |
| Metaprogramação — registro de rotas | `estrategias.py` — `RotaColeta.__init_subclass__` e `_registro_rotas`; `ESTRATEGIAS_VALIDAS = set(FABRICA_ROTAS)` |
| **Strategy** | `estrategias.py` — `RotaColeta`, `RotaDireta`, `RotaComDuplaConferencia`, trocáveis em `robo.estrategia` |
| **Command** | `comandos.py` — `ComandoColeta.executar`/`.desfazer`; histórico em `RoboColetor.processar_pedido`/`desfazer_ultima_coleta` |
| **Factory** | `fabrica.py` — `criar_robo_coletor` (registro) e `criar_robo_configurado` (validação + montagem) |
| **Observer** | `observadores.py` — `EquipeDeTestes`, `RegistroAuditoria`, `DespachanteTransporte` |
| **State** | `modos.py` — `ModoColetando`, `ModoAguardandoVerificacao`; transição disparada pelo Observer |
| Modelo de features / LPS | `modelo_features.py` — 4 dimensões (tipo, rota, área, marcação do item), `REQUER`, `EXCLUI`, `EXCLUI_AREA_POR_TIPO`, `validar_configuracao` |
| Hierarquia de exceções | `excecoes.py` — `ErroColeta` → `ConfiguracaoInvalida`, `PedidoInvalido` |
| Configuração e persistência | `persistencia.py` — `montar_robo_de_config`, `montar_pedido_de_json`, `carregar_lote`, `salvar_auditoria` |
| CLI | `cli.py` + `main.py` |
| Testes | `tests/test_configuracao.py`, `tests/test_pedido.py`, `tests/test_fluxo_completo.py` |

## Testes

`pytest -v` roda limpo a partir da raiz. Além dos 2 testes fornecidos em
`tests/test_00_fornecido.py` (não editados), a suíte cobre:

* `pytest.raises(PedidoInvalido)` para codinome inexistente, quantidade acima do
  disponível, pedido vazio, posição fora da grade e item frágil + urgente;
* `@pytest.mark.parametrize` com `itertools.product` sobre
  `TIPOS_VALIDOS × ESTRATEGIAS_VALIDAS × AREAS_VALIDAS`, conferindo o contrato
  inteiro — não só válido/inválido, mas que o robô criado tem exatamente o tipo,
  a rota e a área pedidos, e que a área realmente mexe em `robo.obstaculos`;
* a transição `ModoColetando` → `ModoAguardandoVerificacao` acontecendo sozinha
  quando o evento `"bandeja_pronta"` é injetado com `robo.notificar`;
* a área de quarentena bloqueando `avancar()` de fato;
* o fluxo completo (carregar → processar → aprovar), a rejeição mantendo os
  itens, o `desfazer`, a dupla conferência e o handoff coletor → transportador.

## Extensão opcional (Seção 7)

`RoboTransportador` (em `robo.py`) entrou em `Robo._registro` só por herdar de
`Robo` — nenhuma linha de `RoboColetor` precisou mudar, e `TIPOS_VALIDOS`
passou a reconhecê-lo automaticamente (é o que
`test_contrato_criar_ou_recusar` comprova: os casos parametrizados dobraram
sozinhos).

`DespachanteTransporte` é o Observer que faz o handoff: ao receber
`"lote_aprovado"`, cria o transportador pela mesma fábrica, entrega a ele o
conteúdo da bandeja e o leva até o ponto de retirada. A restrição nova é um
`excludes`: `EXCLUI_AREA_POR_TIPO` impede o transportador de entrar na
`"area_quarentena"` — se o coletor estava lá, o despachante registra
`"transporte_recusado"` na auditoria em vez de estourar.
