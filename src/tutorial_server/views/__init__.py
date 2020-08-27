"""
#####################################################
:mod:`~tutorial_server.views` - Tutorial Server Views
#####################################################

This module contains the view handlers for the Tutorial Server.
"""
import filetype
import mimetypes
import os

from decorator import decorator
from io import BytesIO
from pathlib import Path
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
from pyramid.request import Request
from pyramid.response import Response
from pyramid.view import view_config
from zipfile import ZipFile, ZIP_DEFLATED


def includeme(config):
    """Setup the Tutorial Server's routes."""
    settings = config.registry.settings

    config.add_route('root', f'{settings["url.prefix"]}/')
    config.add_route('download', f'{settings["url.prefix"]}/download')
    config.add_route('content.get',
                     f'{config.registry.settings["url.prefix"]}/content/*path',
                     request_method='GET')


@view_config(route_name='root')
def root(request: Request):
    raise HTTPFound(request.route_url('content.get', path=()))


@view_config(route_name='download')
def download(request: Request):
    buffer = BytesIO()
    with ZipFile(buffer, mode='w', compression=ZIP_DEFLATED) as zip_file:
        app_home = os.path.abspath(request.registry.settings['app.home'])
        for basepath, _, filenames in os.walk(app_home):
            for filename in filenames:
                source_filename = os.path.join(basepath, filename)
                target_filename = source_filename[len(app_home) + 1:]
                zip_file.write(source_filename, arcname=target_filename)
                print(target_filename)
    download_filename = 'Content.zip'
    if 'app.download_filename' in request.registry.settings:
        download_filename = request.registry.settings['app.download_filename']
    return Response(body=buffer.getvalue(),
                    headerlist=[('Content-Type', 'application/zip'),
                                ('Content-Disposition', f'attachment; filename={download_filename}')])
