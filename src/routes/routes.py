from src.controllers.controller import home

routes = {
    'home_route': '/',
    'home': home.as_view('olaaa')
}
