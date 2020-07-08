# Tutorial Server

The Tutorial Server is a simple web-server designed primarily for use in a JupyterHub environment.

## Development

To build and run the server locally the following tools are required:

* Python version 3.8 or greater: https://www.python.org/
* Poetry: https://python-poetry.org/

All further local dependencies are installed using the following command:

```
poetry install
```

A configuration file for development purposes is provided and can be run using the following command:

```
pserve --reload development.ini
```
