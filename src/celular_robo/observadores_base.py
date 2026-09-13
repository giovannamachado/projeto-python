# Fornecido pelo professor — NÃO EDITE este arquivo.
#
# `AlertaBateria`/`RegistroEventos` são o Observer genérico do curso
# (bateria) — não têm relação com o domínio de coleta, não reaproveite essas
# classes.
#
# `Observador` é a classe abstrata do padrão (`ABC` + `__init_subclass__`/
# `_registro`, mesmo mecanismo de `Robo._registro` em robo_base.py). Seus
# `EquipeDeTestes`/`RegistroAuditoria` (observadores.py, enunciado Seção 2.3)
# devem herdar dela:
#
#   from celular_robo.observadores_base import Observador
#   class EquipeDeTestes(Observador):
#       ...
#
# Herdar registra suas classes automaticamente em `Observador._registro`,
# junto com os observadores de bateria acima — inofensivo, nada no projeto
# valida esse registro (ao contrário de `Robo._registro`/`_registro_rotas`,
# usados em `TIPOS_VALIDOS`/`ESTRATEGIAS_VALIDAS`).

from abc import ABC, abstractmethod


class Observador(ABC):
    _registro = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Observador._registro[cls.__name__] = cls

    @abstractmethod
    def atualizar(self, evento, **dados):
        ...


class AlertaBateria(Observador):
    def atualizar(self, evento, **dados):
        if evento == "bateria_critica":
            print(f"[ALERTA] bateria crítica: {dados['nivel']}%")


class RegistroEventos(Observador):
    def __init__(self):
        self.eventos = []

    def atualizar(self, evento, **dados):
        self.eventos.append((evento, dados))
