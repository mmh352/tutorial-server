"""
######################################################################################
:mod:`~tutorial_server.jupyterhub_ping` - Activity pinging for inclusion in JupyterHub
######################################################################################
"""
from os import environ
from requests import post
from requests.exceptions import ConnectionError
from datetime import datetime
from decorator import decorator
from threading import Timer


last_ping = None
last_activity = None
timer = None
active = False


def includeme(config):
    """Setup the JupyterHub activity pings. The following environment variables **must** be set for this to run:

    * JUPYTERHUB_ACTIVITY_URL
    * JUPYTERHUB_SERVER_NAME
    * JUPYTERHUB_API_TOKEN
    """
    global active, timer
    active = 'JUPYTERHUB_ACTIVITY_URL' in environ and 'JUPYTERHUB_SERVER_NAME' in environ and \
        'JUPYTERHUB_API_TOKEN' in environ
    timer = Timer(60, ping_server)


def ping_server():
    """Ping the JupyterHub activity URL. At most one ping every 60 seconds is sent and a ping will only be sent if
    there was any activity within the last 120 seconds."""
    global active, last_ping, last_activity, timer
    if active:
        if not last_ping or (datetime.utcnow() - last_ping).seconds > 59:
            if last_activity and (datetime.utcnow() - last_activity).seconds < 120:
                try:
                    timestamp = last_activity.isoformat() + 'Z'
                    response = post(environ['JUPYTERHUB_ACTIVITY_URL'],
                                    headers={'Authorization': f'token {environ["JUPYTERHUB_API_TOKEN"]}'},
                                    json={'servers': {environ['JUPYTERHUB_SERVER_NAME']: {'last_activity': timestamp}},
                                          'last_activity': timestamp})
                    if response.status_code == 200:
                        last_ping = datetime.utcnow()
                except ConnectionError:
                    pass
            if timer:
                timer.cancel()
            timer = Timer(60, ping_server)
            timer.start()


def ping_alive():
    """Decorator that updates the last activity timestamp and calls
    :func:`~tutorial_server.jupyterhub_ping.ping_server`."""
    def handler(f, *args, **kwargs):
        global active, last_activity
        if active:
            last_activity = datetime.utcnow()
            ping_server()
        return f(*args, **kwargs)
    return decorator(handler)
