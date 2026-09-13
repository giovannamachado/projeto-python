# Fornecido pelo professor — NÃO EDITE este arquivo.
#
# `ComandoAvancar`/`ComandoGirar`/`ComandoParar` são o Command genérico do
# curso (`Robo.executar(["AVANCAR 3", "GIRAR DIR"])`) — não têm relação com o
# domínio de coleta, não reaproveite essas classes.
#
# `Comando` é a classe abstrata do padrão (`ABC` + `__init_subclass__`/
# `_registro`, mesmo mecanismo de `Robo._registro` em robo_base.py). Seu
# `ComandoColeta` (comandos.py, enunciado Seção 2.3) deve herdar dela:
#
#   from celular_robo.comandos_base import Comando
#   class ComandoColeta(Comando):
#       ...
#
# Herdar registra `ComandoColeta` automaticamente em `Comando._registro`,
# junto com os comandos de movimentação acima — inofensivo, nada no projeto
# valida esse registro (ao contrário de `Robo._registro`/`_registro_rotas`,
# usados em `TIPOS_VALIDOS`/`ESTRATEGIAS_VALIDAS`).

from abc import ABC, abstractmethod


class Comando(ABC):
    _registro = {}

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Comando._registro[cls.__name__] = cls

    @abstractmethod
    def executar(self, robo):
        ...


class ComandoAvancar(Comando):
    def __init__(self, passos):
        self.passos = passos

    def executar(self, robo):
        robo.avancar_n(self.passos)

    def __repr__(self):
        return f"ComandoAvancar({self.passos})"


class ComandoGirar(Comando):
    def __init__(self, lado):
        self.lado = lado

    def executar(self, robo):
        robo.girar(self.lado)

    def __repr__(self):
        return f"ComandoGirar({self.lado!r})"


class ComandoParar(Comando):
    def executar(self, robo):
        print(f"{robo.nome} parou.")

    def __repr__(self):
        return "ComandoParar()"


def parse_comando(texto):
    partes = texto.strip().upper().split()
    acao = partes[0]
    if acao == "AVANCAR":
        return ComandoAvancar(int(partes[1]))
    if acao == "GIRAR":
        return ComandoGirar(partes[1])
    if acao == "PARAR":
        return ComandoParar()
    raise ValueError(f"comando desconhecido: {texto!r}")
