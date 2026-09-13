# RoboColetor + QuantidadeValida — enunciado, Seção 2.1.
#
# `Robo` (posição, __init_subclass__/_registro, avancar/girar, estrategia/modo,
# Observer) já vem pronto em robo_base.py — não precisa reescrever, só importar:
#
#   from celular_robo.robo_base import Robo, Coordenada
#
# TODO: implemente aqui.
# - RoboColetor(Robo): reaproveita Coordenada (x, y) por herança — não precisa
#   redeclarar. Adicione o que for específico da coleta (ex.: bandeja).
# - QuantidadeValida: descriptor novo (mesmo protocolo de Coordenada/Percentual
#   em robo_base.py), validando que a quantidade coletada de um item nunca é
#   negativa nem passa do pedido.
# - __str__/__repr__ (robô) e __len__ (bandeja — quantos itens já coletados).
