"""Cria a aplicação Flask e registra as rotas de `src/routes/routes.py`.

A lógica de cada tela fica em `src/controllers/`; os templates em
`src/templates/` e os arquivos CSS em `src/static/`.
"""
from flask import Flask

from src.auth import dados_do_menu
from src.db import fechar_conexao
from src.routes.routes import routes

app = Flask(__name__)
# Chave usada para assinar a sessão de login. Troque por um valor secreto seu.
app.secret_key = "troque-esta-chave-secreta"
app.teardown_appcontext(fechar_conexao)
app.context_processor(dados_do_menu)

for url, view in routes:
    app.add_url_rule(url, view_func=view)


if __name__ == "__main__":
    app.run(debug=True)
