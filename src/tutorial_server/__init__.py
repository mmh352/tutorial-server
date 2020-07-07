from pyramid.config import Configurator


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    if settings['url.prefix'].endswith('/'):
        settings['url.prefix'] = settings['url.prefix'][:-1]
    config = Configurator(settings=settings)
    config.include('.views')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.add_route('home-one', f'{settings["url.prefix"]}/*fizzle')
    config.add_route('home-two', '/*fizzle')
    config.scan()
    return config.make_wsgi_app()
