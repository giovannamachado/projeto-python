# Robô Coletor de Celulares

Projeto final da disciplina de Python.

Um `RoboColetor` recebe um pedido de coleta, anda pela grade de um laboratório
de testes de celulares, recolhe os protótipos pedidos com o sistema de sucção,
guarda tudo numa bandeja e avisa a bancada quando o lote está pronto. Enquanto
a equipe não aprova a retirada, o robô não aceita pedido novo.

O código roda a partir de arquivos JSON: um com a configuração do robô (tipo,
rota e área), outro com o pedido, e um terceiro com o inventário do lote. Tudo
isso está na pasta `dados/`, e dá para trocar os arquivos sem mexer no código.

## Instalação

Precisa de Python 3.10 ou mais novo e do pytest. O resto é biblioteca padrão.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Rodando

```bash
python main.py
```

Abre um menu com as opções de listar e processar o pedido, ver a bandeja,
aprovar ou rejeitar a retirada, desfazer a última coleta e consultar ou salvar
a trilha de auditoria.

Para usar outros arquivos de entrada:

```bash
python main.py --config dados/config_robo_quarentena.json \
               --pedido dados/pedido_coleta_fragil.json
```

(`--lote` também existe, caso queira apontar para outro inventário.)

Os pedidos de exemplo em `dados/`:

- `pedido_coleta_exemplo.json` roda de ponta a ponta com a configuração padrão;
- `pedido_coleta_fragil.json` só funciona com a rota de dupla conferência, que
  é a da configuração de quarentena;
- `pedido_coleta_conflito.json` mistura item frágil e item urgente de propósito,
  para ver a recusa acontecendo.

## Testes

Na raiz do projeto:

```bash
pytest -v
```

Não precisa instalar o pacote: o `pythonpath = ["src"]` do `pyproject.toml` já
resolve o import.
