import os
import shutil

from decorator import decorator
from importlib.resources import read_text
from pyramid.httpexceptions import HTTPClientError
from pyramid.response import Response
from pyramid.view import view_config
from threading import Thread

from tutorial_server import static


tutorial_ready = False


def includeme(config):
    """Setup the deployment handling."""
    config.add_route('ready', '/ready')
    Thread(group=None, target=deploy_tutorial, kwargs={'config': config}).start()


@view_config(route_name='ready', renderer='json')
def ready_view(request):
    """View that returns the ready status."""
    global tutorial_ready

    return {'status': tutorial_ready}


def deploy_tutorial(config):
    """Deploy the tutorial and workspace."""
    global tutorial_ready

    settings = config.registry.settings
    app_home = os.path.abspath(settings['app.home'])
    app_source = os.path.abspath(settings['app.source'])
    tutorial_home = os.path.join(app_home, 'tutorial')
    workspace_source = os.path.join(tutorial_home, '_static', 'workspace')
    workspace_home = os.path.join(app_home, 'workspace')
    # Deploy the latest version of the tutorial
    if os.path.exists(tutorial_home):
        shutil.rmtree(tutorial_home)
    shutil.copytree(app_source, tutorial_home)
    # Copy any workspace files that do not exist
    if os.path.exists(workspace_source):
        for basepath, _, filenames in os.walk(workspace_source):
            for filename in filenames:
                source_filename = os.path.join(basepath, filename)
                target_filename = os.path.join(workspace_home, source_filename[len(workspace_source) + 1:])
                if not os.path.exists(target_filename):
                    os.makedirs(os.path.dirname(target_filename), exist_ok=True)
                    shutil.copy2(source_filename, target_filename)
    tutorial_ready = True


def require_tutorial_ready():
    """Pyramid decorator to check that the tutorial is ready."""
    global tutorial_ready

    def handler(f, *args, **kwargs):
        if tutorial_ready:
            return f(*args, **kwargs)
        else:
            body = read_text(static, 'loading.html').replace('$ready_url', args[0].route_url('ready'))
            return Response(body=body, content_type='text/html', content_encoding='utf-8')
    return decorator(handler)
