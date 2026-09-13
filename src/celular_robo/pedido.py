"""Pedido de coleta: `ItemPedido` e `Pedido` (Seções 2.4 e 2.6).

Módulo acrescentado à estrutura sugerida no enunciado (justificativa no
README): o pedido é o dado central do projeto e aparece em quase todos os
outros módulos — deixá-lo solto dentro de `persistencia.py` misturaria o
formato do dado com a leitura de arquivo.

Aqui mora só a **forma** do pedido. As regras de negócio sobre ele
(codinome existe no lote? quantidade cabe? `fragil` e `urgente` brigam?)
ficam em `modelo_features.py`, junto com o resto do modelo de features.
"""

from celular_robo.excecoes import PedidoInvalido


class ItemPedido:
    """Uma linha do pedido: o que coletar, onde, e com que cuidado."""

    def __init__(
        self,
        codinome: str,
        quantidade: int,
        posicao,
        fragil: bool = False,
        urgente: bool = False,
    ) -> None:
        self.codinome = codinome
        self.quantidade = quantidade
        self.posicao = tuple(posicao)
        self.fragil = fragil
        self.urgente = urgente

    @classmethod
    def de_dict(cls, bruto: dict) -> "ItemPedido":
        """Converte um item do JSON, recusando o que estiver malformado."""
        if not isinstance(bruto, dict):
            raise PedidoInvalido(f"item do pedido precisa ser um objeto: {bruto!r}")

        codinome = bruto.get("codinome")
        if not isinstance(codinome, str) or not codinome.strip():
            raise PedidoInvalido(f"item sem codinome utilizável: {bruto!r}")

        quantidade = bruto.get("quantidade", 1)
        if not isinstance(quantidade, int) or isinstance(quantidade, bool):
            raise PedidoInvalido(
                f"quantidade de {codinome!r} precisa ser um inteiro, "
                f"recebi {quantidade!r}"
            )
        if quantidade <= 0:
            raise PedidoInvalido(
                f"quantidade de {codinome!r} precisa ser positiva, "
                f"recebi {quantidade}"
            )

        posicao = bruto.get("posicao")
        if (
            not isinstance(posicao, (list, tuple))
            or len(posicao) != 2
            or not all(isinstance(c, int) and not isinstance(c, bool) for c in posicao)
        ):
            raise PedidoInvalido(
                f"posição de {codinome!r} precisa ser [x, y] com inteiros, "
                f"recebi {posicao!r}"
            )

        return cls(
            codinome=codinome,
            quantidade=quantidade,
            posicao=posicao,
            fragil=bool(bruto.get("fragil", False)),
            urgente=bool(bruto.get("urgente", False)),
        )

    @property
    def marcacoes(self) -> set[str]:
        """As marcações ligadas neste item — dimensão `urgência` do modelo."""
        ligadas = set()
        if self.fragil:
            ligadas.add("fragil")
        if self.urgente:
            ligadas.add("urgente")
        return ligadas

    def __repr__(self) -> str:
        return (
            f"ItemPedido({self.codinome!r}, {self.quantidade}, {self.posicao}, "
            f"fragil={self.fragil}, urgente={self.urgente})"
        )

    def __str__(self) -> str:
        marcas = ", ".join(sorted(self.marcacoes)) or "sem marcação"
        return (
            f"{self.quantidade}x {self.codinome} em {self.posicao} [{marcas}]"
        )


class Pedido:
    """Um lote a coletar: nome do lote e a lista de itens."""

    def __init__(self, lote: str, itens) -> None:
        self.lote = lote
        self.itens = list(itens)

    @classmethod
    def de_dict(cls, bruto: dict) -> "Pedido":
        if not isinstance(bruto, dict):
            raise PedidoInvalido(f"pedido precisa ser um objeto JSON: {bruto!r}")
        lote = bruto.get("lote")
        if not isinstance(lote, str) or not lote.strip():
            raise PedidoInvalido("pedido sem nome de lote")
        itens_brutos = bruto.get("itens")
        if not isinstance(itens_brutos, list):
            raise PedidoInvalido(f"pedido {lote!r} não traz uma lista de itens")
        return cls(lote, [ItemPedido.de_dict(item) for item in itens_brutos])

    @property
    def total_unidades(self) -> int:
        return sum(item.quantidade for item in self.itens)

    @property
    def codinomes(self) -> list[str]:
        return [item.codinome for item in self.itens]

    def marcacoes(self) -> set[str]:
        """União das marcações de todos os itens do pedido."""
        marcas: set[str] = set()
        for item in self.itens:
            marcas |= item.marcacoes
        return marcas

    def __len__(self) -> int:
        return len(self.itens)

    def __iter__(self):
        return iter(self.itens)

    def __getitem__(self, indice):
        return self.itens[indice]

    def __repr__(self) -> str:
        return f"Pedido({self.lote!r}, {len(self.itens)} item(ns))"

    def __str__(self) -> str:
        cabecalho = (
            f"{self.lote} — {len(self.itens)} item(ns), "
            f"{self.total_unidades} unidade(s)"
        )
        return cabecalho + "\n" + "\n".join(f"  {item}" for item in self.itens)
