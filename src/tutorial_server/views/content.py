import filetype
import mimetypes
import os

from decorator import decorator
from pathlib import Path
from os import path
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
from pyramid.request import Request
from pyramid.response import Response
from pyramid.view import view_config

from tutorial_server.deployment import require_tutorial_ready


def resolve_path(base_dir, relative_path, index=('index.html',)):
    """Resolves the ``relative_path`` relative to the ``base_dir``. Will raise
    :class:`~pyramid.httpexceptions.HTTPNotFound` if the ``relative_path`` is not a sub-path of the ``base_dir``
    or no file exists for the resolved path.

    If an ``index`` iterable is provided and the resolved path is a directory, it will test the filenames in
    ``index`` relative to the resolved path. The first matching file is returned.

    :param base_dir:
    :type base_dir: ``str``
    :param relative_path:
    :type relative_path: ``tuple`` of ``str``
    :param index:
    :type index: ``str`` iterable
    :return: The resolved path
    :rtype: :class:`~pathlib.Path`
    """
    file_path = Path(path.join(base_dir, *relative_path))
    file_path = file_path.resolve(strict=True)
    if not str(file_path).startswith(str(Path(base_dir).resolve(strict=True))):
        raise HTTPNotFound()
    if file_path.is_dir():
        matched = None
        for filename in index:
            if file_path.joinpath(filename).is_file():
                matched = filename
                break
        if matched:
            file_path = file_path.joinpath(matched)
    if not file_path.is_file():
        raise HTTPNotFound()
    return file_path


def guess_type(file_path):
    """Guess the mime type of the ``file_path``. Will first attempt to identify the mime type through the file's magic
    number. If that fails, guesses the mime type based on the file extension. Where possible it will also attempt to
    guess the file's encoding.

    :param file_path: The path to get the mime type for
    :type file_path: :class:`~pathlib.Path`
    :return: The mimetype and encoding
    :rtype: ``(mime_type, encoding)``
    """
    file_type = filetype.guess(str(file_path))
    if file_type:
        mime_type = (file_type.mime, None)
    else:
        mime_type = ('text/text', None)
    if mime_type[0] == 'text/text':
        mime_type = mimetypes.guess_type(file_path)
    if not mime_type[0]:
        mime_type = ('text/text', None)
    return mime_type


@view_config(route_name='content.get')
@require_tutorial_ready()
def get_tutorial(request: Request):
    """Fetch a single resource from the tutorial tree."""
    try:
        file_path = resolve_path(os.path.join(request.registry.settings['app.home'], 'tutorial'),
                                 request.matchdict['path'])
        mime_type = guess_type(file_path)
        headerlist = [
            ('X-URL-Prefix', request.registry.settings["url.prefix"][:-len(request.registry.settings["url.app_prefix"])]),
            ('Content-Type', mime_type[0]),
        ]
        if mime_type[1]:
            headerlist = [('Content-Encoding', mime_type[1])]
        return Response(body=file_path.read_bytes(),
                        headerlist=headerlist)
    except FileNotFoundError:
        raise HTTPNotFound()
    except RuntimeError:
        raise HTTPNotFound()
