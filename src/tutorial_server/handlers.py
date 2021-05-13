import filetype
import mimetypes
import os
import subprocess

from asyncio import create_subprocess_exec, wait_for, subprocess
from io import BytesIO
from importlib.resources import read_text
from tornado import web
from tornado.options import options
from zipfile import ZipFile

from .config import config

in_jupyter_hub = os.environ.get('JUPYTERHUB_API_TOKEN') is not None


def guess_mime_type(filepath):
    file_type = filetype.guess(str(filepath))
    if file_type:
        return file_type.mime
    mime_type, encoding = mimetypes.guess_type(filepath)
    if mime_type:
        if encoding == 'gzip':
            return 'application/gzip'
        elif encoding is not None:
            return 'application/octet-stream'
        else:
            return mime_type
    else:
        return 'application/octet-stream'


class DefaultHandler(web.RequestHandler):
    """Default handler that redirects when ready."""

    def prepare(self):
        self.send_error(status_code=404)

    def write_error(self, status_code, exc_info=None):
        if status_code == 404:
            body = read_text('tutorial_server.static', '404.html')
            body = body.replace('${baseurl}', f'{options.basepath}')
            self.write(body)
        elif status_code == 503:
            self.write(read_text('tutorial_server.static', '503.html'))
        self.flush()


class RootHandler(web.RequestHandler):
    """Root handler that redirects when ready."""

    def get(self):
        self.redirect(f'{options.basepath}{config.get("app", "default")}/')

    def post(self):
        self.redirect(f'{options.basepath}{config.get("app", "default")}/')

    def write_error(self, status_code, exc_info=None):
        if status_code == 404:
            body = read_text('tutorial_server.static', '404.html')
            body = body.replace('${baseurl}', f'{options.basepath}')
            self.write(body)
        self.flush()


class TutorialHandler(RootHandler):
    """Handle the requests for the tutorial files."""

    def initialize(self, part=None):
        self._part = part
        self._rootpath = os.path.abspath(os.path.join(config.get('app', 'home'),
                                                      config.get(f'app:{self._part}', 'target')))

    def get(self, path):
        filename = path
        if filename == '' or filename.endswith('/'):
            filename = f'{filename}index.html'
        filepath = os.path.abspath(os.path.join(self._rootpath, filename))
        if filepath.startswith(self._rootpath) and os.path.exists(filepath):
            self.set_header('Content-Type', guess_mime_type(filepath))
            self.set_header('X-URL-prefix', options.basepath)
            if in_jupyter_hub:
                self.set_header('X-in-jupyter-hub', 'true')
            with open(filepath, 'rb') as in_f:
                self.write(in_f.read())
            self.flush()
        else:
            self.send_error(status_code=404)


class WorkspaceHandler(RootHandler):
    """Handle the requests for the editor workspace."""

    def initialize(self, part=None):
        self._part = part
        self._rootpath = os.path.abspath(os.path.join(config.get('app', 'home'),
                                                      config.get(f'app:{self._part}', 'target')))

    def get(self, path):
        filepath = os.path.abspath(os.path.join(self._rootpath, path))
        if filepath.startswith(self._rootpath) and os.path.exists(filepath):
            self.set_header('Content-Type', guess_mime_type(filepath))
            self.set_header('X-URL-prefix', options.basepath)
            if in_jupyter_hub:
                self.set_header('X-in-jupyter-hub', 'true')
            with open(filepath, 'rb') as in_f:
                self.write(in_f.read())
            self.flush()
        else:
            self.send_error(status_code=404)

    def put(self, path):
        filepath = os.path.abspath(os.path.join(self._rootpath, path))
        if filepath.startswith(self._rootpath) and os.path.exists(filepath):
            with open(filepath, 'wb') as out_f:
                out_f.write(self.request.body)
            self.flush()
        else:
            self.send_error(status_code=404)


class LiveHandler(RootHandler):
    """Handle a live site.

    Supports CGI calls for .php files."""

    def initialize(self, part=None):
        self._part = part
        self._rootpath = os.path.abspath(os.path.join(config.get('app', 'home'),
                                                      config.get(f'app:{self._part}', 'target')))

    async def get(self, path):
        filepath = os.path.abspath(os.path.join(self._rootpath, path))
        if filepath.startswith(self._rootpath) and os.path.exists(filepath):
            if filepath.endswith('.php'):
                env = {
                    'GATEWAY_INTERFACE': 'CGI/1.1',
                    'QUERY_STRING': self.request.query,
                    'REDIRECT_STATUS': 'on',
                    'SCRIPT_FILENAME': filepath,
                    'DOCUMENT_ROOT': self._rootpath,
                    'SCRIPT_NAME': filepath[len(self._rootpath):],
                    'REQUEST_METHOD': 'GET'
                }
                proc = await create_subprocess_exec('php-cgi', stdout=subprocess.PIPE, env=env)
                stdout, _ = await wait_for(proc.communicate(), 30)
                lines = stdout.decode('utf-8').split('\n')
                in_headers = True
                for line in lines:
                    line = line.strip()
                    if in_headers:
                        if line == '':
                            in_headers = False
                        elif ':' in line:
                            self.set_header(line[:line.find(':')], line[line.find(':') + 1:])
                    else:
                        self.write(f'{line}\n')
            else:
                self.set_header('Content-Type', guess_mime_type(filepath))
                self.set_header('X-URL-prefix', options.basepath)
                if in_jupyter_hub:
                    self.set_header('X-in-jupyter-hub', 'true')
                with open(filepath, 'rb') as in_f:
                    self.write(in_f.read())
                self.flush()
        else:
            self.send_error(status_code=404)

    async def post(self, path):
        filepath = os.path.abspath(os.path.join(self._rootpath, path))
        if filepath.startswith(self._rootpath) and os.path.exists(filepath):
            if filepath.endswith('.php'):
                env = {
                    'GATEWAY_INTERFACE': 'CGI/1.1',
                    'REDIRECT_STATUS': 'on',
                    'SCRIPT_FILENAME': filepath,
                    'DOCUMENT_ROOT': self._rootpath,
                    'SCRIPT_NAME': filepath[len(self._rootpath):],
                    'REQUEST_METHOD': 'POST',
                    'CONTENT_TYPE': self.request.headers['Content-Type'],
                    'CONTENT_LENGTH': self.request.headers['Content-Length']
                }
                proc = await create_subprocess_exec('php-cgi', stdout=subprocess.PIPE, stdin=subprocess.PIPE, env=env)
                stdout, _ = await wait_for(proc.communicate(self.request.body), 30)
                lines = stdout.decode('utf-8').split('\n')
                in_headers = True
                for line in lines:
                    line = line.strip()
                    if in_headers:
                        if line == '':
                            in_headers = False
                        elif ':' in line:
                            self.set_header(line[:line.find(':')], line[line.find(':') + 1:])
                    else:
                        self.write(f'{line}\n')
            else:
                self.set_header('Content-Type', guess_mime_type(filepath))
                self.set_header('X-URL-prefix', options.basepath)
                if in_jupyter_hub:
                    self.set_header('X-in-jupyter-hub', 'true')
                with open(filepath, 'rb') as in_f:
                    self.write(in_f.read())
                self.flush()
        else:
            self.send_error(status_code=404)


class DownloadHandler(RootHandler):
    """Download handler compresses and sends the complete home directory."""

    def get(self):
        buffer = BytesIO()
        with ZipFile(buffer, mode='w') as zip_file:
            for part in [p.strip() for x in config.get('app', 'parts').split(',') for p in x.split('\n')]:
                if config.has_section(f'app:{part}'):
                    part_path = os.path.join(config.get('app', 'home'), config.get(f'app:{part}', 'target'))
                    home_path = config.get('app', 'home')
                    for basepath, _, filenames in os.walk(part_path):
                        for filename in filenames:
                            filepath = os.path.join(basepath, filename)
                            zip_file.write(filepath, f'{config.get("app", "name")}/{filepath[len(home_path) + 1:]}')
        self.set_header('Content-Type', 'application/zip')
        self.set_header('Content-Disposition', f'attachment; filename={config.get("app", "name")}.zip')
        self.write(buffer.getvalue())
        self.flush()
