from paver.easy import *
from paver.path import path
from paver.setuputils import setup


setup(
    name="actionscript-bundler",
    scripts=['as3bundler.py'],
    version="0.1",
    author="Travis Parker",
    author_email="travis.parker@gmail.com"
)

@task
@needs('generate_setup', 'minilib', 'setuptools.command.sdist')
def sdist():
    pass

@task
def clean():
    for p in map(path, ('actionscript_bundler.egg-info', 'dist', 'setup.py',
                        'paver-minilib.zip', 'build')):
        if p.exists():
            if p.isdir():
                p.rmtree()
            else:
                p.remove()
