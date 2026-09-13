"""Strategy — as rotas de coleta (Seções 2.2 e 2.3).

Segunda hierarquia de metaprogramação do projeto: `RotaColeta` tem o seu
próprio `__init_subclass__`/`_registro_rotas`, em vez de herdar de `Estrategia`
(estrategias_base.py). O motivo está no modelo de features — `ESTRATEGIAS_VALIDAS`
é derivado do registro, e herdar de `Estrategia` traria junto
`EstrategiaPadrao`/`EstrategiaEsquiva`/`EstrategiaZigzag`, que são movimentação
livre do curso e não rotas de coleta.

A chave do registro é o **nome curto** usado na configuração (`"direta"`,
`"dupla_conferencia"`), passado como argumento de classe — mesma ideia do
`categoria="geral"` de `Robo.__init_subclass__`.
"""

from abc import ABC, abstractmethod
from collections import deque

from celular_robo.excecoes import PedidoInvalido
from celular_robo.robo_base import Direcao, Robo


class RotaColeta(ABC):
    """Base das rotas de coleta, com registro automático das subclasses."""

    _registro_rotas: dict[str, type["RotaColeta"]] = {}
    nome_curto: str | None = None
    descricao = "rota de coleta"

    def __init_subclass__(cls, nome_curto: str | None = None, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if nome_curto is not None:
            cls.nome_curto = nome_curto
        RotaColeta._registro_rotas[cls.nome_curto or cls.__name__] = cls

    def __init__(self) -> None:
        self.passos_dados = 0

    # --- interface do Strategy -------------------------------------------
    @abstractmethod
    def coletar(self, robo, comando) -> int:
        """Leva o robô até a prateleira do comando e recolhe o item."""

    def mover(self, robo) -> bool:
        """Um passo avulso — mantém `robo.mover()` (State) funcionando."""
        return self._avancar(robo)

    # --- navegação compartilhada -----------------------------------------
    def navegar_ate(self, robo, destino) -> int:
        """Percorre a grade até `destino`, contornando os obstáculos da área.

        Devolve quantos passos foram dados. Se não existe caminho (o item está
        atrás de uma barreira intransponível, como o corredor de quarentena),
        levanta `PedidoInvalido` — o pedido não é executável nessa área.
        """
        destino = tuple(destino)
        caminho = self._caminho_ate(robo, destino)
        if caminho is None:
            robo.notificar("destino_inalcancavel", destino=destino)
            raise PedidoInvalido(
                f"posição {destino} é inalcançável a partir de {robo.posicao} "
                f"na área {robo.area_nome!r}"
            )
        for casa in caminho:
            self._passo_para(robo, casa)
        return len(caminho)

    def _passo_para(self, robo, casa) -> None:
        """Gira para a casa vizinha e avança um quadrado."""
        dx = casa[0] - robo.x
        dy = casa[1] - robo.y
        robo.girar_ate(Direcao((dx, dy)))
        self._avancar(robo)

    def _avancar(self, robo) -> bool:
        moveu = robo.avancar()
        if moveu:
            self.passos_dados += 1
        return moveu

    @staticmethod
    def _caminho_ate(robo, destino) -> list[tuple[int, int]] | None:
        """Busca em largura na grade: menor caminho livre até `destino`.

        Devolve a lista de casas a percorrer (sem a origem), ou `None` se o
        destino estiver bloqueado ou isolado.
        """
        lado = Robo.LADO_GRADE
        origem = robo.posicao
        if destino == origem:
            return []
        if not (0 <= destino[0] < lado and 0 <= destino[1] < lado):
            return None
        if destino in robo.obstaculos:
            return None

        anterior: dict[tuple[int, int], tuple[int, int] | None] = {origem: None}
        fila = deque([origem])
        while fila:
            atual = fila.popleft()
            for direcao in Direcao:
                dx, dy = direcao.value
                vizinho = (atual[0] + dx, atual[1] + dy)
                if not (0 <= vizinho[0] < lado and 0 <= vizinho[1] < lado):
                    continue
                if vizinho in robo.obstaculos or vizinho in anterior:
                    continue
                anterior[vizinho] = atual
                if vizinho == destino:
                    return RotaColeta._refazer(anterior, destino)
                fila.append(vizinho)
        return None

    @staticmethod
    def _refazer(anterior, destino) -> list[tuple[int, int]]:
        caminho = []
        casa = destino
        while casa is not None:
            caminho.append(casa)
            casa = anterior[casa]
        caminho.reverse()
        return caminho[1:]

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    def __str__(self) -> str:
        return f"{self.nome_curto} ({self.descricao})"


class RotaDireta(RotaColeta, nome_curto="direta"):
    """Vai direto até cada prateleira e aciona a sucção — sem revalidação."""

    descricao = "menor caminho até a prateleira, sem revalidação"

    def coletar(self, robo, comando) -> int:
        self.navegar_ate(robo, comando.posicao)
        return robo.sugar(comando.codinome, comando.quantidade)


class RotaComDuplaConferencia(RotaColeta, nome_curto="dupla_conferencia"):
    """Revalida o item antes e depois da sucção — mais lenta, mais segura.

    É a rota exigida por itens `fragil=True` e a única aceita dentro da área de
    quarentena (modelo_features.py).
    """

    descricao = "confere o item antes e depois de depositar na bandeja"

    def __init__(self) -> None:
        super().__init__()
        self.conferencias = 0

    def mover(self, robo) -> bool:
        """Só avança com o caminho comprovadamente livre pelo sensor."""
        if not robo.sensor_frente():
            return False
        return self._avancar(robo)

    def coletar(self, robo, comando) -> int:
        self.navegar_ate(robo, comando.posicao)
        self._conferir(robo, comando, "antes da sucção")
        coletado = robo.sugar(comando.codinome, comando.quantidade)
        self._conferir(robo, comando, "antes de depositar")
        return coletado

    def _conferir(self, robo, comando, etapa: str) -> None:
        self.conferencias += 1
        if robo.posicao != tuple(comando.posicao):
            raise PedidoInvalido(
                f"conferência falhou {etapa}: {robo.nome} está em "
                f"{robo.posicao}, e {comando.codinome!r} fica em "
                f"{tuple(comando.posicao)}"
            )
        robo.notificar(
            "item_conferido",
            codinome=comando.codinome,
            etapa=etapa,
            posicao=robo.posicao,
        )
