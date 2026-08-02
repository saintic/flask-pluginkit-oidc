import re
import ast
from setuptools import setup


def _get_meta(meta):
    pat = re.compile(r'__%s__\s+=\s+(.*)' % meta)
    with open('flask_pluginkit_oidc/__init__.py', 'rb') as fh:
        meta_str = ast.literal_eval(pat.search(fh.read().decode('utf-8')).group(1))
    return str(meta_str)


def _get_author():
    mail_re = re.compile(r'(.*)\s<(.*)>')
    author = _get_meta("author")
    return (mail_re.search(author).group(1), mail_re.search(author).group(2))


(author, email) = _get_author()
setup(
    name='flask-pluginkit-oidc',
    version=_get_meta("version"),
    license=_get_meta("license"),
    author=author,
    author_email=email,
    url='https://github.com/saintic/flask-pluginkit-oidc',
    keywords="flask-pluginkit",
    description=_get_meta("description"),
    packages=['flask_pluginkit_oidc',],
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'Flask-PluginKit>=3.8.0',
        'authlib>=1.7.0'
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)