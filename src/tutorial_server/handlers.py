import filetype
import mimetypes
import os

from io import BytesIO
from importlib.resources import read_text
from tornado import web
from tornado.options import options
from zipfile import ZipFile

from .config import config
from .content import content_ready, deploy_content


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

    def head(self, *args, **kwargs):
        if not content_ready():
            self.send_error(status_code=503)

    def get(self):
        if content_ready():
            self.redirect(f'{options.basepath}{config.get("app", "default")}/')
        else:
            self.send_error(status_code=503)

    def write_error(self, status_code, exc_info=None):
        if status_code == 404:
            body = read_text('tutorial_server.static', '404.html')
            body = body.replace('${baseurl}', f'{options.basepath}')
            self.write(body)
        elif status_code == 503:
            self.write(read_text('tutorial_server.static', '503.html'))
        self.flush()


class TutorialHandler(RootHandler):

    def initialize(self, part=None):
        self._part = part

    def get(self, path):
        if content_ready():
            filename = path
            if filename == '' or filename.endswith('/'):
                filename = f'{filename}index.html'
            rootpath = os.path.abspath(os.path.join(config.get('app', 'home'), self._part))
            filepath = os.path.abspath(os.path.join(rootpath, filename))
            if filepath.startswith(rootpath) and os.path.exists(filepath):
                self.set_header('Content-Type', guess_mime_type(filepath))
                self.set_header('X-URL-prefix', options.basepath)
                with open(filepath, 'rb') as in_f:
                    self.write(in_f.read())
                self.flush()
            else:
                self.send_error(status_code=404)
        else:
            self.send_error(status_code=503)


class DownloadHandler(RootHandler):

    def get(self):
        if content_ready():
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
        else:
            self.send_error(status_code=503)


class RefreshHandler(RootHandler):
    """The :class:`~tutorial_server.handlers.RefreshHandler` reloads the tutorial content."""

    async def post(self):
        if content_ready():
            await deploy_content()
            self.flush()
        else:
            self.send_error(status_code=503)
