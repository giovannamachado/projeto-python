"""State — os dois modos de operação do robô coletor (Seção 2.3).

`ModoColetando` delega para a rota configurada, do mesmo jeito que
`ModoExplorando` delega para a estratégia genérica do curso.
`ModoAguardandoVerificacao` trava o robô enquanto a equipe de testes não
decide sobre o lote — mesmo papel de `ModoCarregando` recusando `mover()`.

Quem troca de um modo para o outro **não é o modo**: é a `EquipeDeTestes`
(observadores.py) reagindo ao evento `"bandeja_pronta"`, mesmo mecanismo do
`MonitorBateria` de modos_base.py.
"""

from celular_robo.excecoes import ErroColeta
from celular_robo.modos_base import ModoOperacao


class ModoColetando(ModoOperacao):
    """Operação normal: o robô anda e coleta conforme a rota configurada."""

    def mover(self, robo):
        return robo.estrategia.mover(robo)

    def coletar(self, robo, comando) -> int:
        return robo.estrategia.coletar(robo, comando)

    def aceitar_pedido(self, robo, pedido) -> bool:
        return True

    def __repr__(self) -> str:
        return "ModoColetando()"

    def __str__(self) -> str:
        return "coletando"


class ModoAguardandoVerificacao(ModoOperacao):
    """Bandeja completa: tudo parado até a equipe aprovar ou rejeitar o lote."""

    def mover(self, robo):
        print(f"{robo.nome} aguarda verificação da bandeja, não pode se mover.")
        return False

    def coletar(self, robo, comando) -> int:
        raise ErroColeta(
            f"{robo.nome} está aguardando verificação da bandeja — "
            f"não coleta {comando.codinome!r} antes da equipe decidir"
        )

    def aceitar_pedido(self, robo, pedido) -> bool:
        raise ErroColeta(
            f"{robo.nome} só aceita um pedido novo depois que a equipe de "
            f"testes aprovar o lote {robo.nome_do_lote!r}"
        )

    def __repr__(self) -> str:
        return "ModoAguardandoVerificacao()"

    def __str__(self) -> str:
        return "aguardando verificação"
