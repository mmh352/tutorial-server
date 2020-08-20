from pyramid.config import Configurator


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    if settings['url.prefix'].endswith('/'):
        settings['url.prefix'] = settings['url.prefix'][:-1]
    config = Configurator(settings=settings)
    config.include('.deployment')
    config.include('.views')
    config.add_static_view('static', 'static', cache_max_age=3600)
    config.scan()
    return config.make_wsgi_app()
