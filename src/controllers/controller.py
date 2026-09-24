from flask.views import MethodView

class home(MethodView):
    def get(self):
        return 'Olá mundo'
