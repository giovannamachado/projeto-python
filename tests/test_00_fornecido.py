# Fornecido pelo professor — NÃO EDITE este arquivo.
#
# Rode `pytest -v` agora, antes de escrever qualquer código: os 2 testes abaixo
# vão falhar (RoboColetor ainda não existe). É o esperado, não um bug — eles
# ficam verdes conforme você implementa o projeto (ver "Pontapé inicial" no
# enunciado). Servem de contrato mínimo para os nomes que o resto da spec
# espera: RoboColetor, criar_robo_configurado, ConfiguracaoInvalida.

import pytest

from celular_robo.fabrica import criar_robo_configurado
from celular_robo.excecoes import ConfiguracaoInvalida


@pytest.fixture
def robo_padrao():
    return criar_robo_configurado(
        "RoboColetor", "Coletor-1",
        estrategia_nome="direta", area_nome="centro_padrao",
    )


def test_robo_padrao_comeca_na_origem(robo_padrao):
    assert (robo_padrao.x, robo_padrao.y) == (0, 0)


def test_area_quarentena_exclui_rota_direta():
    with pytest.raises(ConfiguracaoInvalida):
        criar_robo_configurado(
            "RoboColetor", "Coletor-2",
            estrategia_nome="direta", area_nome="area_quarentena",
        )
