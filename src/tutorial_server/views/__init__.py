"""
#####################################################
:mod:`~tutorial_server.views` - Tutorial Server Views
#####################################################

This module contains the view handlers for the Tutorial Server.
"""
import filetype
import mimetypes

from decorator import decorator
from pathlib import Path
from os import path
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
from pyramid.request import Request
from pyramid.response import Response
from pyramid.view import view_config


def includeme(config):
    """Setup the Tutorial Server's routes."""
    settings = config.registry.settings

    config.add_route('root', f'{settings["url.prefix"]}/')

    config.add_route('tutorial.get',
                     f'{config.registry.settings["url.prefix"]}/tutorial/*path',
                     request_method='GET')

    if 'app.proxy' in settings:
        print(settings['app.proxy'])


@view_config(route_name='root')
def root(request: Request):
    raise HTTPFound(request.route_url('tutorial.get', path=()))
