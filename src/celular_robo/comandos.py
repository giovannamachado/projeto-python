"""Command — cada item do pedido vira um `ComandoColeta` (Seção 2.3).

A novidade em relação ao Command visto no curso é o `desfazer`: o comando
guarda quanto efetivamente coletou e sabe devolver isso à prateleira,
decrementando a bandeja.
"""

from celular_robo.comandos_base import Comando
from celular_robo.excecoes import ErroColeta


class ComandoColeta(Comando):
    """Recolhe `quantidade` unidades de `codinome`, guardadas em `posicao`."""

    def __init__(self, codinome: str, posicao, quantidade: int = 1) -> None:
        self.codinome = codinome
        self.posicao = tuple(posicao)
        self.quantidade = quantidade
        self.coletado = 0

    @classmethod
    def de_item(cls, item) -> "ComandoColeta":
        """Constrói o comando a partir de um `ItemPedido` (pedido.py)."""
        return cls(item.codinome, item.posicao, item.quantidade)

    def executar(self, robo) -> int:
        """Delega ao modo do robô, que delega à rota configurada."""
        coletado = robo.coletar(self)
        self.coletado += coletado
        return coletado

    def desfazer(self, robo) -> int:
        """Tira da bandeja o que este comando colocou lá."""
        if self.coletado == 0:
            raise ErroColeta(
                f"nada a desfazer: {self.codinome!r} ainda não foi coletado"
            )
        devolvido = self.coletado
        robo.devolver(self.codinome, devolvido)
        self.coletado = 0
        return devolvido

    def __repr__(self) -> str:
        return (
            f"ComandoColeta({self.codinome!r}, {self.posicao}, "
            f"{self.quantidade})"
        )

    def __str__(self) -> str:
        return (
            f"coletar {self.quantidade}x {self.codinome} em {self.posicao} "
            f"({self.coletado} já na bandeja)"
        )


def comandos_do_pedido(pedido) -> list[ComandoColeta]:
    """Traduz o pedido inteiro numa lista de comandos, na ordem dos itens."""
    return [ComandoColeta.de_item(item) for item in pedido]
