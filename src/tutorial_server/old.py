from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from pyramid.response import Response


@view_config(route_name='home-one', renderer='json')
def my_view(request):
    return {'matchdict': list(request.matchdict.items()),
            'route': request.matched_route.name,
            'prefix': request.registry.settings,
            'routes': {'home-one': request.route_url('home-one', fizzle=('a', 'b')),
                       'home-two': request.route_url('home-two', fizzle=('a', 'b'))}}

@view_config(route_name='home-two')
def redirect(request):
    raise HTTPFound(request.route_url('home-one', fizzle=[]))
