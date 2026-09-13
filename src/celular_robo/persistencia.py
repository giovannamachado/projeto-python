"""Configuração e persistência: JSON → robô / pedido (Seção 2.6).

Mesmo par de funções do capstone do curso, com a mesma assimetria intencional:
`montar_robo_de_config` recebe um `dict` já carregado, `montar_pedido_de_json`
recebe um caminho de arquivo.
"""

import json
from pathlib import Path

from celular_robo.excecoes import ConfiguracaoInvalida, ErroColeta
from celular_robo.fabrica import criar_robo_configurado
from celular_robo.modelo_features import validar_pedido
from celular_robo.pedido import Pedido

DIRETORIO_DADOS = Path(__file__).resolve().parents[2] / "dados"
CAMINHO_LOTE = DIRETORIO_DADOS / "lote_testes.json"
CAMINHO_CONFIG = DIRETORIO_DADOS / "config_robo_exemplo.json"
CAMINHO_PEDIDO = DIRETORIO_DADOS / "pedido_coleta_exemplo.json"


def carregar_json(caminho) -> dict:
    """Lê um JSON do disco, traduzindo os erros de leitura para `ErroColeta`."""
    caminho = Path(caminho)
    try:
        with caminho.open(encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except FileNotFoundError as erro:
        raise ErroColeta(f"arquivo não encontrado: {caminho}") from erro
    except json.JSONDecodeError as erro:
        raise ErroColeta(f"JSON inválido em {caminho}: {erro}") from erro


def carregar_lote(caminho=CAMINHO_LOTE) -> dict[str, int]:
    """Inventário do lote: codinome → unidades disponíveis na prateleira.

    O JSON do pedido só traz o *nome* do lote; é este arquivo que diz o que
    existe de fato para coletar, e é contra ele que `validar_pedido` compara.
    """
    bruto = carregar_json(caminho)
    disponivel = bruto.get("disponivel")
    if not isinstance(disponivel, dict):
        raise ErroColeta(f"{caminho} não traz o mapa 'disponivel'")

    estoque: dict[str, int] = {}
    for codinome, unidades in disponivel.items():
        if not isinstance(unidades, int) or isinstance(unidades, bool) or unidades < 0:
            raise ErroColeta(
                f"estoque de {codinome!r} precisa ser um inteiro não negativo, "
                f"recebi {unidades!r}"
            )
        estoque[codinome] = unidades
    return estoque


def montar_robo_de_config(config: dict):
    """Monta o robô a partir de um dicionário de configuração já carregado."""
    if not isinstance(config, dict):
        raise ConfiguracaoInvalida(
            f"configuração precisa ser um objeto JSON, recebi {type(config).__name__}"
        )
    faltando = {"tipo_nome", "nome"} - set(config)
    if faltando:
        raise ConfiguracaoInvalida(
            f"configuração incompleta, faltam: {sorted(faltando)}"
        )
    return criar_robo_configurado(
        config["tipo_nome"],
        config["nome"],
        estrategia_nome=config.get("estrategia_nome", "direta"),
        area_nome=config.get("area_nome", "centro_padrao"),
        x=config.get("x", 0),
        y=config.get("y", 0),
    )


def montar_robo_de_json(caminho=CAMINHO_CONFIG):
    """Atalho de conveniência para a CLI: arquivo → `montar_robo_de_config`."""
    return montar_robo_de_config(carregar_json(caminho))


def montar_pedido_de_json(
    caminho=CAMINHO_PEDIDO, estoque: dict | None = None
) -> Pedido:
    """Lê o pedido do disco e o valida contra o inventário do lote."""
    pedido = Pedido.de_dict(carregar_json(caminho))
    if estoque is None:
        estoque = carregar_lote()
    validar_pedido(pedido, estoque)
    return pedido


def salvar_auditoria(auditoria, caminho) -> Path:
    """Grava a trilha de auditoria em JSON, para consulta posterior."""
    caminho = Path(caminho)
    linhas = [
        {
            "instante": linha.instante,
            "evento": linha.evento,
            "robo": linha.robo,
            "dados": {chave: str(valor) for chave, valor in linha.dados.items()},
        }
        for linha in auditoria
    ]
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8") as arquivo:
        json.dump(linhas, arquivo, ensure_ascii=False, indent=2)
    return caminho
