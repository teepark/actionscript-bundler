from paver.easy import *
import paver.doctools
from paver.setuputils import setup


setup(
    name="actionscript-bundler",
    packages=['as3bundler'],
    scripts=['as3bundler/as3bundler.py'],
    version="0.1",
    author="Travis Parker",
    author_email="travis.parker@gmail.com"
)
