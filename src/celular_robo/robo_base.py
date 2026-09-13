# Fornecido pelo professor — NÃO EDITE este arquivo.
#
# `Robo` (+ descriptors, Direcao, Sensor/Radio) do fim do curso — já pronto,
# testado em sala. Congelado aqui pra todo mundo da turma construir
# `RoboColetor` sobre a mesma base, sem divergência entre soluções por causa
# de um bug ou lacuna que tenha sobrado no seu `Robo` pessoal das aulas
# anteriores. As três subclasses de exemplo (`RoboVeloz`, `RoboExplorador`,
# `RoboBlindado`) foram removidas — não fazem parte deste domínio e
# poluiriam `Robo._registro` com tipos que não são `RoboColetor`.
#
# `RoboColetor` (em robo.py) herda de `Robo` e reaproveita `self.estrategia`/
# `self.modo` pros seus próprios Strategy/State (RotaDireta/RotaComDuplaConferencia,
# ModoColetando/ModoAguardandoVerificacao) — mesmo mecanismo de dispatch,
# domínio novo. Os patterns genéricos do curso (Strategy/Command/Observer/
# State que `Robo` usa como valor padrão, e o Factory `criar_robo`) ficam em
# estrategias_base.py/comandos_base.py/observadores_base.py/modos_base.py/
# fabrica_base.py — um arquivo por pattern, mesma separação que o resto do
# projeto usa pros seus próprios patterns, em vez de tudo empilhado num
# arquivo só.

from enum import Enum

from celular_robo.comandos_base import ComandoParar, parse_comando
from celular_robo.estrategias_base import EstrategiaPadrao
from celular_robo.modos_base import ModoCarregando, ModoExplorando


class Coordenada:
    def __init__(self, minimo, maximo):
        self.minimo = minimo
        self.maximo = maximo

    def __set_name__(self, owner, name):
        self.nome_publico = name
        self.nome = "_" + name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__[self.nome]

    def __set__(self, instance, valor):
        if not (self.minimo <= valor < self.maximo):
            raise ValueError(
                f"{self.nome_publico}={valor} sai da grade "
                f"({self.minimo} a {self.maximo - 1})"
            )
        instance.__dict__[self.nome] = valor


class Percentual:
    def __set_name__(self, owner, name):
        self.nome = "_" + name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__[self.nome]

    def __set__(self, instance, valor):
        instance.__dict__[self.nome] = max(0, min(100, valor))


class Direcao(Enum):
    LESTE = (1, 0)
    NORTE = (0, 1)
    OESTE = (-1, 0)
    SUL = (0, -1)

    def virar_esquerda(self):
        ordem = [Direcao.LESTE, Direcao.NORTE, Direcao.OESTE, Direcao.SUL]
        return ordem[(ordem.index(self) + 1) % 4]

    def virar_direita(self):
        ordem = [Direcao.LESTE, Direcao.NORTE, Direcao.OESTE, Direcao.SUL]
        return ordem[(ordem.index(self) - 1) % 4]

    def oposta(self):
        dx, dy = self.value
        return Direcao((-dx, -dy))


class Sensor:
    def __init__(self, alcance=1):
        self.alcance = alcance

    def ler(self, robo):
        dx, dy = robo.direcao.value
        for passo in range(1, self.alcance + 1):
            nx, ny = robo.x + dx * passo, robo.y + dy * passo
            if not (0 <= nx < Robo.LADO_GRADE and 0 <= ny < Robo.LADO_GRADE):
                return False
            if (nx, ny) in robo.obstaculos:
                return False
        return True


class Radio:
    def __init__(self, alcance=5):
        self.alcance = alcance

    def transmitir(self, mensagem):
        return f"[alcance {self.alcance}] {mensagem}"


class Robo:
    LADO_GRADE = 10
    x = Coordenada(0, LADO_GRADE)
    y = Coordenada(0, LADO_GRADE)
    bateria = Percentual()
    _registro = {}

    def __init_subclass__(cls, categoria="geral", **kwargs):
        super().__init_subclass__(**kwargs)
        Robo._registro[cls.__name__] = cls
        cls.categoria = categoria

    def __init__(self, nome, x=0, y=0, direcao=Direcao.LESTE, obstaculos=None,
                 bateria=100, alcance_sensor=1, alcance_radio=5, estrategia=None,
                 modo=None):
        self.nome = nome
        self.x = x
        self.y = y
        self.direcao = direcao
        self.trajetoria = [(x, y)]
        self.obstaculos = obstaculos if obstaculos is not None else {}
        self.bateria = bateria
        self.sensor = Sensor(alcance_sensor)
        self.radio = Radio(alcance_radio)
        self.estrategia = estrategia if estrategia is not None else EstrategiaPadrao()
        self.modo = modo if modo is not None else ModoExplorando()
        self._historico_comandos = []
        self._observadores = []

    def __repr__(self):
        return f"Robo({self.nome!r}, x={self.x}, y={self.y}, direcao={self.direcao})"

    def __str__(self):
        return f"{self.nome} em ({self.x}, {self.y}), direção {self.direcao.name}"

    def __len__(self):
        return len(self.trajetoria)

    def __iter__(self):
        return iter(self.trajetoria)

    def __getattr__(self, nome_attr):
        cache = self.__dict__.setdefault("_cache_leituras", {})
        if nome_attr in cache:
            return cache[nome_attr]
        if nome_attr.startswith("leitura_"):
            direcao_nome = nome_attr.removeprefix("leitura_").upper()
            try:
                direcao = Direcao[direcao_nome]
            except KeyError:
                raise AttributeError(f"Robo não tem atributo {nome_attr!r}") from None
            dx, dy = direcao.value
            nx, ny = self.x + dx, self.y + dy
            livre = (0 <= nx < Robo.LADO_GRADE and 0 <= ny < Robo.LADO_GRADE
                     and (nx, ny) not in self.obstaculos)
            cache[nome_attr] = livre
            return livre
        raise AttributeError(f"Robo não tem atributo {nome_attr!r}")

    def __setattr__(self, nome_attr, valor):
        log = self.__dict__.setdefault("_log_mudancas", [])
        if nome_attr != "_log_mudancas":
            log.append((nome_attr, valor))
        super().__setattr__(nome_attr, valor)

    @property
    def direcao(self):
        return self._direcao

    @direcao.setter
    def direcao(self, valor):
        if not isinstance(valor, Direcao):
            raise TypeError(f"direcao precisa ser Direcao, recebi {type(valor).__name__}")
        self._direcao = valor

    @property
    def posicao(self):
        return (self.x, self.y)

    @property
    def historico(self):
        return tuple(self._historico_comandos)

    @property
    def bateria_critica(self):
        return self.bateria <= 20

    def sensor_frente(self):
        return self.sensor.ler(self)

    def avancar(self):
        if self.sensor_frente():
            dx, dy = self.direcao.value
            self.x += dx
            self.y += dy
            self.trajetoria.append((self.x, self.y))
            self.__dict__.pop("_cache_leituras", None)
            return True
        self.notificar("obstaculo", posicao=(self.x, self.y))
        return False

    def avancar_n(self, passos):
        for _ in range(passos):
            if not self.avancar():
                break

    def girar(self, lado):
        if lado == "ESQ":
            self.direcao = self.direcao.virar_esquerda()
        elif lado == "DIR":
            self.direcao = self.direcao.virar_direita()

    def mover(self):
        return self.modo.mover(self)

    def executar(self, comandos):
        for texto in comandos:
            cmd = parse_comando(texto)
            cmd.executar(self)
            if isinstance(cmd, ComandoParar):
                break
            self._historico_comandos.append(cmd)

    def adicionar_observador(self, obs):
        self._observadores.append(obs)

    def notificar(self, evento, **dados):
        dados.setdefault("robo", self)
        for obs in self._observadores:
            obs.atualizar(evento, **dados)

    def gastar_bateria(self, quantidade):
        estava_critica = self.bateria_critica
        self.bateria = max(0, self.bateria - quantidade)
        if self.bateria_critica and not estava_critica:
            self.notificar("bateria_critica", nivel=self.bateria)

    def tick(self):
        if isinstance(self.modo, ModoCarregando):
            self.modo.carregar(self)

    def resetar(self):
        self.x = 0
        self.y = 0
        self.direcao = Direcao.LESTE
        self.trajetoria = [(0, 0)]

    def esta_na_borda(self):
        x_borda = self.x == 0 or self.x == Robo.LADO_GRADE - 1
        y_borda = self.y == 0 or self.y == Robo.LADO_GRADE - 1
        return x_borda or y_borda

    def girar_ate(self, direcao_alvo):
        giros = 0
        while self.direcao != direcao_alvo:
            self.girar("DIR")
            giros += 1
        return giros
