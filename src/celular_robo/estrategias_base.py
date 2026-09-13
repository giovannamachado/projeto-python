# Fornecido pelo professor — NÃO EDITE este arquivo.
#
# `EstrategiaPadrao`/`EstrategiaEsquiva`/`EstrategiaZigzag` são o Strategy
# genérico do curso (movimentação livre pela grade) — não têm relação com o
# domínio de coleta, não reaproveite essas classes. `EstrategiaPadrao` é o
# valor padrão de `Robo.estrategia` (ver robo_base.py) quando nenhuma é
# passada.
#
# Diferente de Command/Observer/State (comandos_base.py/observadores_base.py/
# modos_base.py), aqui você NÃO deve herdar de `Estrategia` pra escrever
# `RotaDireta`/`RotaComDuplaConferencia` (estrategias.py, enunciado Seção
# 2.3): escreva sua própria base `RotaColeta`, com seu próprio
# `__init_subclass__`/`_registro_rotas` (enunciado Seção 2.2). Motivo: o
# modelo de features deriva `ESTRATEGIAS_VALIDAS = set(_registro_rotas)`
# direto do registro (Seção 2.4) — se `RotaDireta` herdasse de `Estrategia`,
# esse conjunto viria contaminado com `EstrategiaPadrao`/`Esquiva`/`Zigzag`.
# Para Command/Observer/State não existe essa restrição (nada deriva um
# `_VALIDOS` do registro deles), por isso lá herdar direto da classe
# abstrata é seguro.
#
# `Estrategia` é ABC + `__init_subclass__`/`_registro` — mesmo mecanismo de
# `Robo._registro` (robo_base.py), mais um exemplo pronto do idioma antes de
# você escrever o seu para `RotaColeta`.

from abc import ABC, abstractmethod


class Estrategia(ABC):
    _registro = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Estrategia._registro[cls.__name__] = cls

    @abstractmethod
    def mover(self, robo):
        ...


class EstrategiaPadrao(Estrategia):
    def mover(self, robo):
        return robo.avancar()


class EstrategiaEsquiva(Estrategia):
    def mover(self, robo):
        tentativas = 0
        while not robo.sensor_frente() and tentativas < 4:
            robo.girar("DIR")
            tentativas += 1
        return robo.avancar()


class EstrategiaZigzag(Estrategia):
    def __init__(self, periodo=2):
        self.periodo = periodo
        self.passos_dados = 0

    def mover(self, robo):
        if self.passos_dados > 0 and self.passos_dados % self.periodo == 0:
            lado = "DIR" if (self.passos_dados // self.periodo) % 2 else "ESQ"
            robo.girar(lado)
        moveu = robo.avancar()
        if moveu:
            self.passos_dados += 1
        return moveu
