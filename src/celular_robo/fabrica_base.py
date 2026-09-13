# Fornecido pelo professor — NÃO EDITE este arquivo.
#
# Factory genérico do curso: `criar_robo(tipo_nome, nome, **kwargs)` cria
# qualquer tipo registrado em `Robo._registro` (robo_base.py) — hoje só
# `"RoboColetor"`, já que as subclasses de exemplo foram removidas. Ao
# contrário dos outros `*_base.py` (Strategy/Command/Observer/State
# genéricos, sem relação com o domínio), este é **diretamente reutilizável**:
# `criar_robo("RoboColetor", nome, **kwargs)` já funciona. `criar_robo_coletor`
# (enunciado, Seção 2.3) pode chamar esta função, ou reimplementar o mesmo
# padrão — os dois são aceitos. `criar_robo_configurado` (que combina isso
# com a validação do modelo de features) é todo seu, vai em fabrica.py.

from celular_robo.robo_base import Robo


def criar_robo(tipo_nome, nome, **kwargs):
    classe = Robo._registro.get(tipo_nome)
    if classe is None:
        disponiveis = ", ".join(sorted(Robo._registro))
        raise ValueError(f"tipo desconhecido: {tipo_nome!r}. Disponíveis: {disponiveis}")
    return classe(nome, **kwargs)
