"""Modelo de features / LPS do robô coletor (Seção 2.4).

Quatro dimensões:

1. **tipo de robô** — `TIPOS_VALIDOS`, derivado de `Robo._registro`;
2. **rota de coleta** — `ESTRATEGIAS_VALIDAS`, derivado de
   `RotaColeta._registro_rotas`;
3. **tipo de área** — `AREAS_VALIDAS`, derivado de `FABRICA_AREAS`; cada área
   produz um `robo.obstaculos` diferente, não é só um rótulo;
4. **marcação do item** (`fragil`/`urgente`) — `MARCACOES_VALIDAS`, a dimensão
   que vem no pedido e não na configuração do robô.

Nenhum dos três primeiros conjuntos é digitado à mão: um tipo de robô novo
(`RoboTransportador`, Seção 7) ou uma rota nova entram no modelo só por
existirem, via `__init_subclass__`.
"""

from celular_robo import robo as _robo  # noqa: F401  (registra os tipos)
from celular_robo.estrategias import RotaColeta
from celular_robo.excecoes import ConfiguracaoInvalida, PedidoInvalido
from celular_robo.robo_base import Robo


# --- dimensão 3: áreas do laboratório ------------------------------------
def area_centro_padrao() -> dict:
    """Centro de testes comum: corredores livres, nenhum obstáculo."""
    return {}


def area_quarentena() -> dict:
    """Área com o corredor de quarentena isolado — barreira de verdade.

    A coluna `x = 5` fica bloqueada de `y = 0` a `y = 6`: é por onde ficam as
    unidades com defeito. O robô não atravessa (`avancar()` falha), só contorna
    pelo topo da grade.
    """
    corredor = [(5, y) for y in range(0, 7)]
    return {posicao: True for posicao in corredor}


FABRICA_AREAS = {
    "centro_padrao": area_centro_padrao,
    "area_quarentena": area_quarentena,
}

# --- os conjuntos válidos, todos derivados dos registros ------------------
TIPOS_VALIDOS = set(Robo._registro)
FABRICA_ROTAS = RotaColeta._registro_rotas
ESTRATEGIAS_VALIDAS = set(FABRICA_ROTAS)
AREAS_VALIDAS = set(FABRICA_AREAS)
MARCACOES_VALIDAS = {"fragil", "urgente"}

# --- restrições entre features -------------------------------------------
# excludes: a área de quarentena não permite trajeto sem revalidação.
EXCLUI = {
    "area_quarentena": {"direta"},
}

# excludes (Seção 7): o transportador não entra na área das unidades com defeito.
EXCLUI_AREA_POR_TIPO = {
    "RoboTransportador": {"area_quarentena"},
}

# requires: cada marcação do item exige uma rota capaz de atendê-la.
REQUER = {
    "fragil": {"dupla_conferencia"},
    "urgente": {"direta"},
}


def validar_configuracao(
    tipo_nome: str,
    estrategia_nome: str = "direta",
    area_nome: str = "centro_padrao",
) -> None:
    """Recusa a combinação inválida **antes** de instanciar qualquer robô."""
    if tipo_nome not in TIPOS_VALIDOS:
        raise ConfiguracaoInvalida(
            f"tipo de robô desconhecido: {tipo_nome!r}. "
            f"Disponíveis: {sorted(TIPOS_VALIDOS)}"
        )
    if estrategia_nome not in ESTRATEGIAS_VALIDAS:
        raise ConfiguracaoInvalida(
            f"rota de coleta desconhecida: {estrategia_nome!r}. "
            f"Disponíveis: {sorted(ESTRATEGIAS_VALIDAS)}"
        )
    if area_nome not in AREAS_VALIDAS:
        raise ConfiguracaoInvalida(
            f"área desconhecida: {area_nome!r}. Disponíveis: {sorted(AREAS_VALIDAS)}"
        )
    if area_nome in EXCLUI_AREA_POR_TIPO.get(tipo_nome, set()):
        raise ConfiguracaoInvalida(
            f"{tipo_nome} não opera na área {area_nome!r}"
        )
    if estrategia_nome in EXCLUI.get(area_nome, set()):
        raise ConfiguracaoInvalida(
            f"a área {area_nome!r} exclui a rota {estrategia_nome!r} — "
            f"corredor isolado não permite trajeto sem revalidação"
        )


def validar_item(item) -> None:
    """Checa um item isolado: `fragil` e `urgente` juntos se contradizem.

    A escolha aqui é `PedidoInvalido` (e não `ConfiguracaoInvalida`): o item é
    contraditório sozinho, sem olhar para robô nenhum — exigiria
    `dupla_conferencia` por ser frágil e `direta` por ser urgente ao mesmo
    tempo. É um defeito do conteúdo do pedido.
    """
    if item.fragil and item.urgente:
        raise PedidoInvalido(
            f"{item.codinome!r} está marcado como frágil e urgente ao mesmo "
            f"tempo — exigiria {sorted(REQUER['fragil'])} e "
            f"{sorted(REQUER['urgente'])} na mesma coleta"
        )


def validar_pedido(pedido, estoque: dict) -> None:
    """Valida o conteúdo do pedido contra o inventário do lote.

    O pedido é rejeitado **inteiro** ao primeiro problema, sem coletar nada —
    ver a justificativa no README (atomicidade).
    """
    if len(pedido) == 0:
        raise PedidoInvalido(f"o pedido do lote {pedido.lote!r} está vazio")

    acumulado: dict[str, int] = {}
    for item in pedido:
        validar_item(item)

        if item.codinome not in estoque:
            raise PedidoInvalido(
                f"codinome {item.codinome!r} não consta no lote — "
                f"disponíveis: {sorted(estoque)}"
            )

        x, y = item.posicao
        if not (0 <= x < Robo.LADO_GRADE and 0 <= y < Robo.LADO_GRADE):
            raise PedidoInvalido(
                f"posição {item.posicao} de {item.codinome!r} está fora da "
                f"grade de {Robo.LADO_GRADE}x{Robo.LADO_GRADE}"
            )

        acumulado[item.codinome] = acumulado.get(item.codinome, 0) + item.quantidade
        if acumulado[item.codinome] > estoque[item.codinome]:
            raise PedidoInvalido(
                f"o pedido quer {acumulado[item.codinome]} unidade(s) de "
                f"{item.codinome!r}, mas o lote só tem "
                f"{estoque[item.codinome]}"
            )

    marcacoes = pedido.marcacoes()
    if "fragil" in marcacoes and "urgente" in marcacoes:
        raise PedidoInvalido(
            f"o pedido do lote {pedido.lote!r} mistura itens frágeis e "
            f"urgentes — um robô tem uma rota só, e as duas marcações exigem "
            f"rotas diferentes"
        )


def rotas_exigidas(pedido) -> set[str]:
    """As rotas que atendem a **todas** as marcações presentes no pedido."""
    exigidas = ESTRATEGIAS_VALIDAS
    for marcacao in pedido.marcacoes():
        exigidas = exigidas & REQUER.get(marcacao, ESTRATEGIAS_VALIDAS)
    return exigidas


def validar_pedido_para_rota(pedido, estrategia_nome: str) -> None:
    """`requires`: a rota do robô precisa dar conta das marcações do pedido."""
    for item in pedido:
        for marcacao in sorted(item.marcacoes):
            aceitas = REQUER.get(marcacao)
            if aceitas and estrategia_nome not in aceitas:
                raise ConfiguracaoInvalida(
                    f"{item.codinome!r} é {marcacao} e exige uma destas rotas: "
                    f"{sorted(aceitas)} — o robô está configurado com "
                    f"{estrategia_nome!r}"
                )
