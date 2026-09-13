"""CLI do robô coletor (Seção 4).

Menu interativo por cima das mesmas funções que os testes usam. Os caminhos dos
arquivos de configuração/pedido/lote podem ser trocados por `argparse`:

    python -m celular_robo.cli
    python -m celular_robo.cli --config dados/config_robo_quarentena.json \
                               --pedido dados/pedido_coleta_fragil.json
"""

import argparse

from celular_robo.excecoes import ErroColeta
from celular_robo.observadores import DespachanteTransporte
from celular_robo.persistencia import (
    CAMINHO_CONFIG,
    CAMINHO_LOTE,
    CAMINHO_PEDIDO,
    carregar_lote,
    montar_pedido_de_json,
    montar_robo_de_json,
    salvar_auditoria,
)

OPCOES = """
 1) Listar o pedido carregado
 2) Processar o pedido
 3) Ver o estado da bandeja
 4) Aprovar a retirada do lote
 5) Rejeitar o lote
 6) Desfazer a última coleta
 7) Ver a trilha de auditoria
 8) Carregar outro pedido
 9) Salvar a trilha de auditoria em JSON
 0) Sair
"""


def montar_argumentos() -> argparse.ArgumentParser:
    analisador = argparse.ArgumentParser(
        prog="celular_robo",
        description="Robô coletor de celulares — laboratório de testes.",
    )
    analisador.add_argument(
        "--config", default=CAMINHO_CONFIG,
        help="JSON de configuração do robô (tipo, rota, área).",
    )
    analisador.add_argument(
        "--pedido", default=CAMINHO_PEDIDO,
        help="JSON do pedido de coleta.",
    )
    analisador.add_argument(
        "--lote", default=CAMINHO_LOTE,
        help="JSON com o inventário do lote (codinome → disponível).",
    )
    return analisador


def cabecalho(robo, pedido) -> str:
    linhas = [
        "=" * 60,
        f" {robo}",
        f" rota: {robo.estrategia} | área: {robo.area_nome} | "
        f"modo: {robo.modo}",
    ]
    if pedido is None:
        linhas.append(" pedido: nenhum carregado")
    else:
        linhas.append(
            f" pedido: {pedido.lote} — {len(pedido)} item(ns), "
            f"{pedido.total_unidades} unidade(s)"
        )
    linhas.append("=" * 60)
    return "\n".join(linhas)


def listar_pedido(robo) -> None:
    if robo.pedido is None:
        print("Nenhum pedido carregado.")
        return
    print(robo.pedido)


def processar(robo) -> None:
    coletadas = robo.processar_pedido()
    print(f"{coletadas} unidade(s) coletada(s).")
    print(robo.bandeja)


def ver_bandeja(robo) -> None:
    print(robo.bandeja)
    print(
        f"Total na bandeja: {len(robo.bandeja)} unidade(s) — "
        f"{'completa' if robo.bandeja.completa else 'incompleta'}."
    )


def aprovar(robo) -> None:
    conteudo = robo.equipe.aprovar(robo)
    print("Lote liberado para retirada:")
    for item in conteudo:
        print(f"  {item.codinome}: {item.coletada} unidade(s)")


def rejeitar(robo) -> None:
    motivo = input("Motivo da rejeição: ").strip() or "não informado"
    lote = robo.equipe.rejeitar(robo, motivo)
    print(f"Lote {lote!r} rejeitado — os itens continuam na bandeja.")


def desfazer(robo) -> None:
    comando = robo.desfazer_ultima_coleta()
    print(f"Desfeito: {comando!r}")
    print(robo.bandeja)


def ver_auditoria(robo) -> None:
    if not len(robo.auditoria):
        print("Nenhum evento registrado ainda.")
        return
    for linha in robo.auditoria.linhas():
        print(f"  {linha}")


def carregar_outro_pedido(robo, caminho_padrao, estoque) -> None:
    caminho = input(f"Caminho do pedido [{caminho_padrao}]: ").strip()
    pedido = montar_pedido_de_json(caminho or caminho_padrao, estoque=estoque)
    robo.carregar_pedido(pedido)
    print(f"Pedido {pedido.lote!r} carregado.")


def salvar_trilha(robo) -> None:
    caminho = input("Arquivo de saída [auditoria.json]: ").strip() or "auditoria.json"
    print(f"Trilha gravada em {salvar_auditoria(robo.auditoria, caminho)}")


def executar_opcao(escolha: str, robo, caminho_pedido, estoque) -> None:
    if escolha == "1":
        listar_pedido(robo)
    elif escolha == "2":
        processar(robo)
    elif escolha == "3":
        ver_bandeja(robo)
    elif escolha == "4":
        aprovar(robo)
    elif escolha == "5":
        rejeitar(robo)
    elif escolha == "6":
        desfazer(robo)
    elif escolha == "7":
        ver_auditoria(robo)
    elif escolha == "8":
        carregar_outro_pedido(robo, caminho_pedido, estoque)
    elif escolha == "9":
        salvar_trilha(robo)
    else:
        print("Opção inválida.")


def main(argv=None) -> int:
    argumentos = montar_argumentos().parse_args(argv)

    try:
        robo = montar_robo_de_json(argumentos.config)
        estoque = carregar_lote(argumentos.lote)
        pedido = montar_pedido_de_json(argumentos.pedido, estoque=estoque)
        robo.adicionar_observador(DespachanteTransporte())
        robo.carregar_pedido(pedido)
    except ErroColeta as erro:
        print(f"{type(erro).__name__}: {erro}")
        return 1

    while True:
        print(cabecalho(robo, robo.pedido))
        print(OPCOES)
        try:
            escolha = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if escolha == "0":
            print("Até mais.")
            return 0
        try:
            executar_opcao(escolha, robo, argumentos.pedido, estoque)
        except ErroColeta as erro:
            print(f"{type(erro).__name__}: {erro}")
        print()


if __name__ == "__main__":
    raise SystemExit(main())
