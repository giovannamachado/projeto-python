"""Factory — da configuração validada até o robô pronto (Seção 2.3).

Dois níveis, como no curso:

* `criar_robo_coletor` é o nível baixo — vai direto no `Robo._registro`
  (reaproveitando `criar_robo`, de fabrica_base.py) e não sabe nada sobre o
  modelo de features;
* `criar_robo_configurado` é a função pública: valida a combinação inteira
  (`validar_configuracao`) e só então monta o robô, já com a rota, a área e os
  observadores da bancada no lugar. É a que a CLI usa.
"""

from celular_robo.excecoes import ConfiguracaoInvalida
from celular_robo.fabrica_base import criar_robo
from celular_robo.modelo_features import (
    FABRICA_AREAS,
    FABRICA_ROTAS,
    validar_configuracao,
)
from celular_robo.modos import ModoColetando
from celular_robo.observadores import EquipeDeTestes, RegistroAuditoria


def criar_robo_coletor(tipo_nome: str, nome: str, **kwargs):
    """Instancia um tipo registrado em `Robo._registro`, sem validar o modelo."""
    try:
        return criar_robo(tipo_nome, nome, **kwargs)
    except ValueError as erro:
        # `criar_robo` (fornecido) levanta ValueError; aqui tudo o que é erro de
        # configuração vira `ConfiguracaoInvalida`, para quem chama poder usar
        # um `except ErroColeta` só.
        raise ConfiguracaoInvalida(str(erro)) from erro


def criar_robo_configurado(
    tipo_nome: str,
    nome: str,
    estrategia_nome: str = "direta",
    area_nome: str = "centro_padrao",
    com_observadores: bool = True,
    **kwargs,
):
    """Valida a configuração e devolve o robô montado e observado."""
    validar_configuracao(tipo_nome, estrategia_nome, area_nome)

    robo = criar_robo_coletor(
        tipo_nome,
        nome,
        obstaculos=FABRICA_AREAS[area_nome](),
        area_nome=area_nome,
        modo=ModoColetando(),
        **kwargs,
    )
    robo.estrategia = FABRICA_ROTAS[estrategia_nome]()

    if com_observadores:
        robo.auditoria = RegistroAuditoria()
        robo.equipe = EquipeDeTestes()
        robo.adicionar_observador(robo.auditoria)
        robo.adicionar_observador(robo.equipe)

    return robo
