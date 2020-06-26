def includeme(config):
    config.add_route('tutorial', f'{config.registry.settings["url.prefix"]}/tutorial/*path')
