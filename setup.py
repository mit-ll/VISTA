from setuptools import setup

setup(
    name='vista',
    version='0.1.0',
    packages=['vista'],
    description = "V2V Identity, Security, and Trust Architecture (VISTA) proof of concept",
    author = "Ian Jessen <ian.jessen@ll.mit.edu>",
    url = "https://llcad-github.llan.ll.mit.edu/acasx/vista/",
    install_requires=[
        'Charm-Crypto',
        'fastapi',
        'uvicorn',
        'typer',
        'pydantic[dotenv,email]',
        'requests',
        'SQLAlchemy',
        'cryptography'
    ],
    python_requires = '~=3.7'
)
