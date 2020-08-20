import os
import requests
import shutil
import tarfile

from decorator import decorator
from importlib.resources import read_text
from pyramid.httpexceptions import HTTPClientError
from pyramid.response import Response
from pyramid.view import view_config
from threading import Thread
from zipfile import ZipFile

from tutorial_server import static


tutorial_ready = False


def includeme(config):
    """Setup the deployment handling."""
    config.add_route('ready', f'{config.registry.settings["url.prefix"]}/ready')
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
    if os.path.exists(settings['app.tmp']):
        shutil.rmtree(settings['app.tmp'])
    deploy_content(settings['app.source'], settings['app.home'], settings['app.tmp'])
    deploy_workspace(settings['app.home'], settings['app.tmp'])
    if os.path.exists(settings['app.tmp']):
        shutil.rmtree(settings['app.tmp'])
    tutorial_ready = True


def deploy_content(app_source, home_dir, tmp_dir):
    """Deploy the tutorial content."""
    if app_source.startswith('http://') or app_source.startswith('https://'):
        source_url, target_filename = app_source.split('$$')
        response = requests.get(source_url)
        if response.status_code == 200:
            os.makedirs(tmp_dir, exist_ok=True)
            with open(os.path.join(tmp_dir, target_filename), 'wb') as out_f:
                out_f.write(response.content)
            deploy_content(os.path.join(tmp_dir, target_filename), home_dir, tmp_dir)
    else:
        if app_source.endswith('.zip'):
            with ZipFile(app_source) as zip_file:
                zip_file.extractall(os.path.join(tmp_dir, 'tutorial'))
            deploy_content(os.path.join(tmp_dir, 'tutorial'), home_dir, tmp_dir)
        elif app_source.endswith('.tar.bz2'):
            with tarfile.open(app_source, mode='r:bz2') as tar_file:
                tar_file.extractall(os.path.join(tmp_dir, 'tutorial'))
            deploy_content(os.path.join(tmp_dir, 'tutorial'), home_dir, tmp_dir)
        elif app_source.endswith('.tar.gz'):
            with tarfile.open(app_source, mode='r:gz') as tar_file:
                tar_file.extractall(os.path.join(tmp_dir, 'tutorial'))
            deploy_content(os.path.join(tmp_dir, 'tutorial'), home_dir, tmp_dir)
        else:
            content_dir = os.path.join(home_dir, 'tutorial')
            if os.path.exists(content_dir):
                shutil.rmtree(content_dir)
            shutil.copytree(app_source, content_dir)


def deploy_workspace(home_dir, tmp_dir):
    """Deploy the tutorial workspace."""
    workspace_source = os.path.join(tmp_dir, 'tutorial', '_static', 'workspace')
    workspace_dir = os.path.join(home_dir, 'workspace')
    if os.path.exists(workspace_source):
        for basepath, _, filenames in os.walk(workspace_source):
            for filename in filenames:
                source_filename = os.path.join(basepath, filename)
                target_filename = os.path.join(workspace_dir, source_filename[len(workspace_source) + 1:])
                if not os.path.exists(target_filename):
                    os.makedirs(os.path.dirname(target_filename), exist_ok=True)
                    shutil.copy2(source_filename, target_filename)


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
