"""Observer — quem acompanha o robô coletor (Seção 2.3).

`EquipeDeTestes` é também o ponto onde Observer e State se encontram: é ela
que troca o modo do robô ao receber `"bandeja_pronta"`, exatamente como o
`MonitorBateria` de modos_base.py troca para `ModoCarregando`. O modo não
decide sozinho que a bandeja acabou.
"""

from collections import namedtuple
from datetime import datetime

from celular_robo.excecoes import ErroColeta
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
