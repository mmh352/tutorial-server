import asyncio

from logging import getLogger
from tornado import ioloop, web
from tornado.options import define, options, parse_command_line

from .config import config, setup_config
from .content import deploy_content
from .handlers import DefaultHandler, RootHandler, TutorialHandler, DownloadHandler


define('config', default='production.ini', help='The configuration file to load')
define('basepath', default='/', help='The URL basepath set by the JupyterHub')
define('port', default=6543, type=int, help='The port to use')
parse_command_line()
setup_config()

logger = getLogger('tutorial_server')


async def startup(app):
    logger.debug('Server initialising')
    await deploy_content()
    logger.debug('Server initialised')


def start_server():
    if not options.basepath.endswith('/'):
        options.basepath = options.basepath + '/'
    if not options.basepath.startswith('/'):
        options.basepath = '/' + options.basepath
    logger.debug(f'Creating the application at {options.basepath} ({options.port})')
    handlers = [
        (f'{options.basepath}', RootHandler),
        (f'{options.basepath}download', DownloadHandler),
    ]
    for part in [p.strip() for x in config.get('app', 'parts').split(',') for p in x.split('\n')]:
        if config.has_section(f'app:{part}'):
            if config.get(f'app:{part}', 'type') == 'tutorial':
                handlers.append((f'{options.basepath}{part}/(.*)',
                                 TutorialHandler,
                                 {'part': part}))
    app = web.Application(handlers,
                          default_handler_class=DefaultHandler)
    app.listen(address=config.get('server', 'host'),
               port=options.port)
    asyncio.get_event_loop().create_task(startup(app))
    logger.debug('Starting the server')
    ioloop.IOLoop.current().start()


start_server()
