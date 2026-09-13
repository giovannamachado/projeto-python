"""`RoboColetor`, a `Bandeja` e o descriptor `QuantidadeValida` — Seção 2.1.

`Robo` (descriptors de posição, `__init_subclass__`/`_registro`, `avancar`/
`girar`, Observer) vem pronto de `robo_base.py`; aqui só entra o que é
específico da coleta.
"""

from celular_robo.comandos import ComandoColeta, comandos_do_pedido
from celular_robo.excecoes import ErroColeta, PedidoInvalido
from celular_robo.modos import ModoColetando
from celular_robo.robo_base import Robo


class QuantidadeValida:
    """Descriptor de quantidade coletada — mesmo protocolo de `Coordenada`.

    Garante a invariante da bandeja: a quantidade coletada de um item nunca é
    negativa nem ultrapassa o que o pedido solicitou. O teto não é fixo como o
    da grade — é lido de outro atributo da própria instância (por padrão
    `solicitada`), porque cada item do pedido tem o seu.
    """

    def __init__(self, limite: str = "solicitada") -> None:
        self.limite = limite

    def __set_name__(self, owner, name: str) -> None:
        self.nome_publico = name
        self.nome = "_" + name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__[self.nome]

    def __set__(self, instance, valor: int) -> None:
        if not isinstance(valor, int) or isinstance(valor, bool):
            raise TypeError(
                f"{self.nome_publico} precisa ser int, recebi "
                f"{type(valor).__name__}"
            )
        maximo = getattr(instance, self.limite)
        if valor < 0:
            raise ValueError(f"{self.nome_publico}={valor} não pode ser negativa")
        if valor > maximo:
            raise ValueError(
                f"{self.nome_publico}={valor} passa do solicitado ({maximo})"
            )
        instance.__dict__[self.nome] = valor


class ItemBandeja:
    """Uma linha da bandeja: quanto foi pedido de um codinome e quanto já entrou."""

    coletada = QuantidadeValida()

    def __init__(self, codinome: str, solicitada: int) -> None:
        self.codinome = codinome
        self.solicitada = solicitada
        self.coletada = 0

    @property
    def completo(self) -> bool:
        return self.coletada == self.solicitada

    @property
    def restante(self) -> int:
        return self.solicitada - self.coletada

    def __repr__(self) -> str:
        return (
            f"ItemBandeja({self.codinome!r}, {self.coletada}/{self.solicitada})"
        )


class Bandeja:
    """Bandeja de saída do robô.

    Classe própria (em vez de um `dict` solto dentro do `RoboColetor`) pra
    concentrar a invariante de quantidade num lugar só e ganhar `__len__`/
    `__iter__`/`__contains__` de graça.
    """

    def __init__(self) -> None:
        self._itens: dict[str, ItemBandeja] = {}

    def reservar(self, codinome: str, quantidade: int) -> ItemBandeja:
        """Abre (ou amplia) a linha de um codinome antes da coleta começar."""
        item = self._itens.get(codinome)
        if item is None:
            item = ItemBandeja(codinome, quantidade)
            self._itens[codinome] = item
        else:
            item.solicitada += quantidade
        return item

    def guardar(self, codinome: str, quantidade: int = 1) -> int:
        item = self._exigir(codinome)
        item.coletada += quantidade
        return item.coletada

    def retirar(self, codinome: str, quantidade: int = 1) -> int:
        item = self._exigir(codinome)
        item.coletada -= quantidade
        return item.coletada

    def _exigir(self, codinome: str) -> ItemBandeja:
        item = self._itens.get(codinome)
        if item is None:
            raise PedidoInvalido(
                f"{codinome!r} não faz parte do pedido carregado na bandeja"
            )
        return item

    def esvaziar(self) -> None:
        self._itens.clear()

    @property
    def completa(self) -> bool:
        """Todos os itens do pedido coletados nas quantidades solicitadas."""
        return bool(self._itens) and all(
            item.completo for item in self._itens.values()
        )

    @property
    def itens(self) -> tuple[ItemBandeja, ...]:
        return tuple(self._itens.values())

    def quantidade_de(self, codinome: str) -> int:
        item = self._itens.get(codinome)
        return item.coletada if item else 0

    def __len__(self) -> int:
        """Quantas unidades já foram coletadas (Seção 2.1)."""
        return sum(item.coletada for item in self._itens.values())

    def __iter__(self):
        return iter(self._itens.values())

    def __contains__(self, codinome: object) -> bool:
        return codinome in self._itens

    def __repr__(self) -> str:
        return f"Bandeja({len(self)} unidade(s), {len(self._itens)} codinome(s))"

    def __str__(self) -> str:
        if not self._itens:
            return "bandeja vazia"
        linhas = [
            f"  {item.codinome}: {item.coletada}/{item.solicitada}"
            for item in self._itens.values()
        ]
        estado = "completa" if self.completa else "em andamento"
        return f"Bandeja ({estado}):\n" + "\n".join(linhas)


class RoboColetor(Robo, categoria="coleta"):
    """Robô que percorre o laboratório recolhendo protótipos numa bandeja.

    Herda posição validada por descriptor, `avancar`/`girar`, o registro
    automático de tipos e o Observer de `Robo` (robo_base.py). O que entra aqui
    é o domínio de coleta: bandeja, sistema de sucção e o pedido em andamento.
    """

    def __init__(self, nome: str, area_nome: str = "centro_padrao", **kwargs) -> None:
        kwargs.setdefault("modo", ModoColetando())
        super().__init__(nome, **kwargs)
        self.area_nome = area_nome
        self.bandeja = Bandeja()
        self.pedido = None
        self._comandos_pendentes = []

    # --- pedido -----------------------------------------------------------
    def carregar_pedido(self, pedido) -> None:
        """Prepara a bandeja para um pedido novo.

        Dois portões antes de aceitar: o modo atual (`ModoAguardandoVerificacao`
        recusa) e o `requires` do modelo de features (um item frágil não entra
        num robô configurado com a rota direta).
        """
        # Import local de propósito: `modelo_features` importa este módulo para
        # que `Robo._registro` já esteja populado quando ele deriva
        # `TIPOS_VALIDOS`. Importar lá em cima fecharia o ciclo.
        from celular_robo.modelo_features import validar_pedido_para_rota

        self.modo.aceitar_pedido(self, pedido)
        validar_pedido_para_rota(pedido, self.estrategia.nome_curto)
        self.pedido = pedido
        self.bandeja.esvaziar()
        self._descartar_comandos_de_coleta()
        for item in pedido:
            self.bandeja.reservar(item.codinome, item.quantidade)
        self._comandos_pendentes = comandos_do_pedido(pedido)

    def _descartar_comandos_de_coleta(self) -> None:
        """Esquece os comandos do pedido anterior (pendentes e desfazíveis).

        A bandeja acabou de ser esvaziada ou liberada, então desfazer uma
        coleta antiga não teria o que devolver. O que aconteceu continua
        registrado na auditoria, que é a trilha de verdade; `_historico_comandos`
        é só a pilha de `desfazer`.
        """
        self._comandos_pendentes = []
        self._historico_comandos = [
            comando
            for comando in self._historico_comandos
            if not isinstance(comando, ComandoColeta)
        ]

    def processar_pedido(self) -> int:
        """Executa o pedido carregado item a item, guardando o histórico.

        Cada item vira um `ComandoColeta`; os comandos executados vão para
        `_historico_comandos` (o mesmo histórico do Command do curso), que é o
        que torna o `desfazer` possível depois.
        """
        if self.pedido is None:
            raise PedidoInvalido(f"{self.nome} não tem pedido carregado")
        total = 0
        while self._comandos_pendentes:
            comando = self._comandos_pendentes[0]
            # Só sai da fila depois de executar sem erro: se a coleta falhar no
            # meio do pedido (item inalcançável, modo recusando), o comando
            # continua pendente e uma nova chamada retoma daqui, sem repetir o
            # que já está na bandeja.
            total += comando.executar(self)
            self._historico_comandos.append(self._comandos_pendentes.pop(0))
        return total

    def coletar(self, comando) -> int:
        """Executa uma coleta passando pelo modo atual (State) e pela rota."""
        return self.modo.coletar(self, comando)

    def desfazer_ultima_coleta(self) -> ComandoColeta:
        """Desfaz o último `ComandoColeta` do histórico (undo do Command)."""
        if not self._historico_comandos:
            raise ErroColeta(f"{self.nome} não tem coleta para desfazer")
        comando = self._historico_comandos[-1]
        # `desfazer` primeiro: se ele levantar, o comando continua no histórico
        # e a pilha não fica furada.
        comando.desfazer(self)
        self._historico_comandos.pop()
        self._comandos_pendentes.insert(0, comando)
        return comando

    # --- sistema de sucção ------------------------------------------------
    def sugar(self, codinome: str, quantidade: int = 1) -> int:
        """Aciona a sucção: tira `quantidade` da prateleira e põe na bandeja."""
        self.bandeja.guardar(codinome, quantidade)
        self.notificar(
            "item_coletado",
            codinome=codinome,
            quantidade=quantidade,
            posicao=self.posicao,
        )
        if self.bandeja.completa:
            self.notificar(
                "bandeja_pronta",
                lote=self.nome_do_lote,
                unidades=len(self.bandeja),
            )
        return quantidade

    def devolver(self, codinome: str, quantidade: int = 1) -> int:
        """Inverso da sucção — usado pelo `desfazer` do `ComandoColeta`."""
        restantes = self.bandeja.retirar(codinome, quantidade)
        self.notificar(
            "coleta_desfeita", codinome=codinome, quantidade=quantidade
        )
        if not self.bandeja.completa:
            self.notificar("bandeja_reaberta", lote=self.nome_do_lote)
        return restantes

    # --- estado -----------------------------------------------------------
    @property
    def nome_do_lote(self) -> str:
        return self.pedido.lote if self.pedido is not None else "sem lote"

    @property
    def bandeja_pronta(self) -> bool:
        return self.bandeja.completa

    def liberar_bandeja(self) -> tuple:
        """Entrega o conteúdo da bandeja e a deixa limpa para o próximo lote."""
        conteudo = self.bandeja.itens
        self.bandeja.esvaziar()
        self.pedido = None
        self._descartar_comandos_de_coleta()
        return conteudo

    def __repr__(self) -> str:
        return (
            f"RoboColetor({self.nome!r}, x={self.x}, y={self.y}, "
            f"rota={type(self.estrategia).__name__}, "
            f"modo={type(self.modo).__name__})"
        )

    def __str__(self) -> str:
        return (
            f"{self.nome} em ({self.x}, {self.y}) — {type(self.modo).__name__}, "
            f"{len(self.bandeja)} unidade(s) na bandeja"
        )


class RoboTransportador(Robo, categoria="transporte"):
    """Extensão opcional (Seção 7): leva o lote aprovado até o ponto de retirada.

    Não precisou de uma linha sequer em `RoboColetor` para existir — herdar de
    `Robo` já o registra em `Robo._registro`, e `TIPOS_VALIDOS` passa a
    reconhecê-lo automaticamente.
    """

    PONTO_DE_RETIRADA = (9, 9)

    def __init__(self, nome: str, area_nome: str = "centro_padrao", **kwargs) -> None:
        kwargs.setdefault("modo", ModoColetando())
        super().__init__(nome, **kwargs)
        self.area_nome = area_nome
        self.carga: dict[str, int] = {}

    def receber(self, itens) -> int:
        """Recebe da bandeja aprovada do coletor as unidades a transportar."""
        for item in itens:
            self.carga[item.codinome] = (
                self.carga.get(item.codinome, 0) + item.coletada
            )
        self.notificar("carga_recebida", unidades=len(self))
        return len(self)

    def entregar(self) -> dict[str, int]:
        """Descarrega no ponto de retirada — só se o robô já estiver lá."""
        if self.posicao != self.PONTO_DE_RETIRADA:
            raise ErroColeta(
                f"{self.nome} precisa estar em {self.PONTO_DE_RETIRADA} para "
                f"entregar, está em {self.posicao}"
            )
        entregue = dict(self.carga)
        self.carga.clear()
        self.notificar("carga_entregue", itens=entregue)
        return entregue

    def __len__(self) -> int:
        return sum(self.carga.values())

    def __repr__(self) -> str:
        return f"RoboTransportador({self.nome!r}, carga={len(self)})"

    def __str__(self) -> str:
        return f"{self.nome} transportando {len(self)} unidade(s)"
