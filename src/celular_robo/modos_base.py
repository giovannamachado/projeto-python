# Fornecido pelo professor — NÃO EDITE este arquivo.
#
# `ModoExplorando`/`ModoCarregando` são o State genérico do curso (bateria) —
# não têm relação com o domínio de coleta, não reaproveite essas classes.
# `ModoExplorando` é o valor padrão de `Robo.modo` (ver robo_base.py) quando
# nenhum é passado.
#
# `ModoOperacao` é a classe abstrata do padrão (`ABC` + `__init_subclass__`/
# `_registro`, mesmo mecanismo de `Robo._registro` em robo_base.py). Seus
# `ModoColetando`/`ModoAguardandoVerificacao` (modos.py, enunciado Seção 2.3)
# devem herdar dela:
#
#   from celular_robo.modos_base import ModoOperacao
#   class ModoColetando(ModoOperacao):
#       ...
#
# Herdar registra suas classes automaticamente em `ModoOperacao._registro`,
# junto com os modos de bateria acima — inofensivo, nada no projeto valida
# esse registro (ao contrário de `Robo._registro`/`_registro_rotas`, usados
# em `TIPOS_VALIDOS`/`ESTRATEGIAS_VALIDAS`).

from abc import ABC, abstractmethod

from celular_robo.observadores_base import Observador


class ModoOperacao(ABC):
    _registro = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        ModoOperacao._registro[cls.__name__] = cls

    @abstractmethod
    def mover(self, robo):
        ...


class ModoExplorando(ModoOperacao):
    def mover(self, robo):
        return robo.estrategia.mover(robo)


class ModoCarregando(ModoOperacao):
    def mover(self, robo):
        print(f"{robo.nome} está carregando, não pode se mover.")
        return False

    def carregar(self, robo):
        robo.bateria = min(100, robo.bateria + 30)
        if robo.bateria >= 100:
            robo.modo = ModoExplorando()


class MonitorBateria(Observador):
    def atualizar(self, evento, **dados):
        if evento == "bateria_critica":
            dados["robo"].modo = ModoCarregando()
