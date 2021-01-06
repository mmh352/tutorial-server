""":mod:`tutorial_server.content` - Content loading functionality
##############################################################
"""
import filetype
import os
import shutil
import tarfile

from logging import getLogger
from tornado.httpclient import AsyncHTTPClient
from zipfile import ZipFile

from .config import config


logger = getLogger('tutorial_server.content')

ready_flag = False


def content_ready():
    """Check if the content has been deployed and is ready.

    :return: ``True`` if the content is deployed and ready, ``False`` otherwise.
    :return_type: ``bool``
    """
    return ready_flag


async def deploy_content():
    """Deploy the tutorial's content.

    Fetches and deploys the latest version of the configured tutorial and all its parts. Sets the ready flag when the
    content has been deployed.
    """
    global ready_flag
    if os.path.exists(config.get('app', 'tmp')):
        logger.debug('Clearing old temporary files')
        shutil.rmtree(config.get('app', 'tmp'))
    await fetch_content(config.get('app', 'source'))
    for part in [p.strip() for x in config.get('app', 'parts').split(',') for p in x.split('\n')]:
        if config.has_section(f'app:{part}'):
            deploy_part(part)
    if os.path.exists(config.get('app', 'tmp')):
        logger.debug('Clearing temporary files')
        shutil.rmtree(config.get('app', 'tmp'))
    ready_flag = True


async def fetch_content(source):
    """Fetch the latest content files.

    The content files are made available in the app:tmp/content directory. If the source is a zip, tar.bz2, or tar.gz
    file, then it is first extracted. If the source is a http or https URL, then it is fetched before being extracted.
    """
    logger.debug('Fetching latest content')
    if source.startswith('http://') or source.startswith('https://'):
        client = AsyncHTTPClient()
        headers = {}
        if config.has_option('app', 'source.auth') and config.has_option('app', 'source.auth.token'):
            headers['Authorization'] = f'bearer {config.get("app", "source.auth.token")}'
        response = await client.fetch(source, headers=headers)
        if response.code == 200:
            os.makedirs(config.get('app', 'tmp'), exist_ok=True)
            with open(os.path.join(config.get('app', 'tmp'), 'download'), 'wb') as out_f:
                out_f.write(response.body)
            file_type = filetype.guess(os.path.join(config.get('app', 'tmp'), 'download'))
            target = None
            if file_type:
                if file_type.mime == 'application/zip':
                    target = os.path.join(config.get('app', 'tmp'), 'download.zip')
                elif file_type.mime == 'application/x-bzip2':
                    target = os.path.join(config.get('app', 'tmp'), 'download.tar.bz2')
                elif file_type.mime == 'application/gzip':
                    target = os.path.join(config.get('app', 'tmp'), 'download.tar.gz')
            if target:
                os.rename(os.path.join(config.get('app', 'tmp'), 'download'), target)
                await fetch_content(target)
            else:
                logger.error('Unsupported download file')
    else:
        if source.endswith('.zip'):
            logger.debug('Extracting from zip file')
            with ZipFile(source) as zip_file:
                zip_file.extractall(os.path.join(config.get('app', 'tmp'), 'content'))
        elif source.endswith('.tar.bz2'):
            logger.debug('Extracting from tar.bz2 file')
            with tarfile.open(source, mode='r:bz2') as tar_file:
                tar_file.extractall(os.path.join(config.get('app', 'tmp'), 'content'))
        elif source.endswith('.tar.gz'):
            logger.debug('Extracting from tar.gz file')
            with tarfile.open(source, mode='r:gz') as tar_file:
                tar_file.extractall(os.path.join(config.get('app', 'tmp'), 'content'))
        else:
            logger.debug('Copying from directory')
            shutil.copytree(source, os.path.join(config.get('app', 'tmp'), 'content'))


def deploy_part(part):
    """Deploy the content of a specific part.

    Uses either :func:`~tutorial_server.content.deploy_tutorial` or :func:`~tutorial_server.content.deploy_workspace`
    to actually deploy the content files.
    """
    logger.debug(f'Deploying part {part}')
    if config.get(f'app:{part}', 'type') == 'tutorial':
        deploy_tutorial(part)
    elif config.get(f'app:{part}', 'type') == 'workspace':
        deploy_workspace(part)
    logger.debug(f'Deployed part {part}')


def deploy_tutorial(part):
    """Deploys a set of tutorial files.

    Tutorial files are treated as static files that are not edited by the student and can thus be overwritten.

    :param part: The name of the part to deploy using the tutorial rules
    :type part: ``str``
    """
    if os.path.exists(os.path.join(config.get('app', 'tmp'), 'content', config.get(f'app:{part}', 'source'))):
        source = os.path.join(config.get('app', 'tmp'), 'content', config.get(f'app:{part}', 'source'))
        target = os.path.join(config.get('app', 'home'), config.get(f'app:{part}', 'target'))
        if os.path.exists(target):
            logger.debug(f'Clearing old {part} files')
            shutil.rmtree(target)
        shutil.copytree(source, target)
    else:
        logger.error(f'Source files for part {part} not found')


def deploy_workspace(part):
    """Deploys a set of workspace files.

    Workspace files are treated as editable files and are thus only deployed if the file does not exist yet.

    :param part: The name of the part to deploy using the workspace rules
    :type part: ``str``
    """
    if os.path.exists(os.path.join(config.get('app', 'tmp'), 'content', config.get(f'app:{part}', 'source'))):
        source = os.path.join(config.get('app', 'tmp'), 'content', config.get(f'app:{part}', 'source'))
        target = os.path.join(config.get('app', 'home'), config.get(f'app:{part}', 'target'))
        if not os.path.exists(target):
            os.makedirs(target, exist_ok=True)
        for basepath, dirnames, filenames in os.walk(source):
            for dirname in dirnames:
                dirname = os.path.join(basepath, dirname)[len(source) + 1:]
                os.makedirs(os.path.join(target, dirname), exist_ok=True)
            for filename in filenames:
                filename = os.path.join(basepath, filename)[len(source) + 1:]
                if not os.path.exists(os.path.join(target, filename)):
                    shutil.copyfile(os.path.join(source, filename), os.path.join(target, filename))
    else:
        logger.error(f'Source files for part {part} not found')
