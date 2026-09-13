"""Observer — quem acompanha o robô coletor (Seção 2.3).

`EquipeDeTestes` é também o ponto onde Observer e State se encontram: é ela
que troca o modo do robô ao receber `"bandeja_pronta"`, exatamente como o
`MonitorBateria` de modos_base.py troca para `ModoCarregando`. O modo não
decide sozinho que a bandeja acabou.
"""

from collections import namedtuple
from datetime import datetime

from celular_robo.excecoes import ConfiguracaoInvalida, ErroColeta
from celular_robo.modos import ModoAguardandoVerificacao, ModoColetando
from celular_robo.observadores_base import Observador

EventoAuditado = namedtuple("EventoAuditado", "instante evento robo dados")


class EquipeDeTestes(Observador):
    """Bancada que recebe os lotes prontos e decide se libera a retirada."""

    def __init__(self, nome: str = "Bancada de Testes") -> None:
        self.nome = nome
        self.lote_pendente: str | None = None
        self.aprovados: list[str] = []
        self.rejeitados: list[tuple[str, str]] = []

    def atualizar(self, evento: str, **dados) -> None:
        robo = dados.get("robo")
        if evento == "bandeja_pronta":
            self.lote_pendente = dados.get("lote")
            robo.modo = ModoAguardandoVerificacao()
            print(
                f"[{self.nome}] lote {self.lote_pendente!r} pronto com "
                f"{dados.get('unidades')} unidade(s) — aguardando verificação."
            )
        elif evento == "bandeja_reaberta" and self.lote_pendente is not None:
            # Uma coleta foi desfeita: o lote deixou de estar completo e o robô
            # volta a coletar sem precisar de aprovação.
            self.lote_pendente = None
            robo.modo = ModoColetando()

    @property
    def aguardando(self) -> bool:
        return self.lote_pendente is not None

    def aprovar(self, robo) -> tuple:
        """Libera a retirada: a bandeja é esvaziada e o robô volta a coletar."""
        lote = self._exigir_lote_pendente()
        conteudo = robo.liberar_bandeja()
        self.aprovados.append(lote)
        self.lote_pendente = None
        robo.modo = ModoColetando()
        robo.notificar("lote_aprovado", lote=lote, itens=conteudo)
        return conteudo

    def rejeitar(self, robo, motivo: str) -> str:
        """Recusa o lote: o robô volta a `ModoColetando` com a bandeja intacta.

        Os itens já coletados permanecem na bandeja — a rejeição é registrada
        pela auditoria, não vira reprocessamento automático (Seção 2.3).
        """
        lote = self._exigir_lote_pendente()
        self.rejeitados.append((lote, motivo))
        self.lote_pendente = None
        robo.modo = ModoColetando()
        robo.notificar("lote_rejeitado", lote=lote, motivo=motivo)
        return lote

    def _exigir_lote_pendente(self) -> str:
        if self.lote_pendente is None:
            raise ErroColeta(
                f"[{self.nome}] não há lote aguardando verificação"
            )
        return self.lote_pendente

    def __repr__(self) -> str:
        return (
            f"EquipeDeTestes({self.nome!r}, pendente={self.lote_pendente!r}, "
            f"aprovados={len(self.aprovados)})"
        )


class RegistroAuditoria(Observador):
    """Trilha de auditoria: registra **todo** evento emitido pelo robô.

    Diferente do `RegistroEventos` do curso (depuração), aqui cada linha
    carrega instante e robô de origem — é o histórico que a equipe consulta
    depois para saber o que aconteceu com um lote.
    """

    def __init__(self) -> None:
        self.eventos: list[EventoAuditado] = []

    def atualizar(self, evento: str, **dados) -> None:
        robo = dados.pop("robo", None)
        self.eventos.append(
            EventoAuditado(
                instante=datetime.now().isoformat(timespec="seconds"),
                evento=evento,
                robo=getattr(robo, "nome", "desconhecido"),
                dados=dados,
            )
        )

    def por_evento(self, evento: str) -> list[EventoAuditado]:
        return [linha for linha in self.eventos if linha.evento == evento]

    def linhas(self) -> list[str]:
        return [
            f"{linha.instante} | {linha.robo} | {linha.evento} | {linha.dados}"
            for linha in self.eventos
        ]

    def __len__(self) -> int:
        return len(self.eventos)

    def __iter__(self):
        return iter(self.eventos)

    def __repr__(self) -> str:
        return f"RegistroAuditoria({len(self.eventos)} evento(s))"


class DespachanteTransporte(Observador):
    """Extensão opcional (Seção 7): o handoff coletor → transportador.

    Reage a `"lote_aprovado"` criando um `RoboTransportador` pela mesma fábrica
    do coletor — sem uma linha nova em `RoboColetor`, porque `TIPOS_VALIDOS`
    vem de `Robo._registro`. Se a área do coletor for a de quarentena, o
    `excludes` do modelo de features recusa o transportador e o despachante
    registra a recusa em vez de estourar.
    """

    def __init__(
        self,
        nome_transportador: str = "Transportador-1",
        area_nome: str | None = None,
    ) -> None:
        self.nome_transportador = nome_transportador
        self.area_nome = area_nome
        self.transportador = None
        self.entregas: list[dict[str, int]] = []

    def atualizar(self, evento: str, **dados) -> None:
        if evento != "lote_aprovado":
            return

        # Import local: `fabrica` importa este módulo para montar os
        # observadores padrão do robô, então o import no topo seria circular.
        from celular_robo.fabrica import criar_robo_configurado
        from celular_robo.robo import RoboTransportador

        coletor = dados["robo"]
        area = self.area_nome or coletor.area_nome
        try:
            transportador = criar_robo_configurado(
                "RoboTransportador",
                self.nome_transportador,
                estrategia_nome="direta",
                area_nome=area,
                com_observadores=False,
            )
        except ConfiguracaoInvalida as erro:
            coletor.notificar(
                "transporte_recusado", lote=dados.get("lote"), motivo=str(erro)
            )
            return

        auditoria = getattr(coletor, "auditoria", None)
        if auditoria is not None:
            transportador.adicionar_observador(auditoria)

        transportador.receber(dados["itens"])
        transportador.estrategia.navegar_ate(
            transportador, RoboTransportador.PONTO_DE_RETIRADA
        )
        self.entregas.append(transportador.entregar())
        self.transportador = transportador

    def __repr__(self) -> str:
        return (
            f"DespachanteTransporte({self.nome_transportador!r}, "
            f"entregas={len(self.entregas)})"
        )
