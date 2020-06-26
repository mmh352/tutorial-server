import filetype
import mimetypes

from pathlib import Path
from os import path
from pyramid.httpexceptions import HTTPNotFound
from pyramid.request import Request
from pyramid.response import Response
from pyramid.view import view_config


@view_config(route_name='tutorial')
def get_tutorial(request: Request):
    try:
        if request.matchdict['path']:
            file_path = Path(path.join(request.registry.settings['app.tutorial_home'], *request.matchdict['path']))
        else:
            file_path = Path(request.registry.settings['app.tutorial_home'])
        file_path = file_path.resolve(strict=True)
        if not str(file_path).startswith(request.registry.settings['app.tutorial_home']):
            raise HTTPNotFound()
        if file_path.is_dir():
            file_path = file_path.joinpath('index.html')
        if not file_path.is_file():
            raise HTTPNotFound()
        # Determine the mimetype and if possible encoding of the file
        file_type = filetype.guess(str(file_path))
        if file_type:
            mime_type = (file_type.mime, None)
        else:
            mime_type = ('text/text', None)
        if mime_type[0] == 'text/text':
            mime_type = mimetypes.guess_type(file_path)
        if not mime_type[0]:
            mime_type = ('text/text', None)
        headerlist = [('Content-Type', mime_type[0])]
        if mime_type[1]:
            headerlist = [('Content-Encoding', mime_type[1])]
        return Response(body=file_path.read_bytes(),
                        headerlist=headerlist)
    except FileNotFoundError:
        raise HTTPNotFound()
    except RuntimeError:
        raise HTTPNotFound()
