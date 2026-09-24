from flask import Flask
from src.routes.routes import routes

app = Flask(__name__)

app.add_url_rule(routes["home_route"], view_func=routes["home"])

