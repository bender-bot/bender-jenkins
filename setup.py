from setuptools import setup

classifiers = [
    'Development Status :: 2 - Pre-Alpha',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
    'Operating System :: POSIX',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: MacOS :: MacOS X',
    'Topic :: Utilities',
]
py_versions = ['2', '2.6', '2.7', '3.4']
classifiers += ['Programming Language :: Python :: %s' % x for x in py_versions]

setup(
    name='bender-jenkins',
    description='bender-jenkins: use Bender to interact with Jenkins CI',
    version='0.1.0',
    url='https://github.com/bender-bot/bender-jenkins',
    license='LGPLv3',
    platforms=['unix', 'linux', 'osx', 'cygwin', 'win32'],
    author='Fabio Menegazzo',
    author_email='menegazzo@gmail.com',
    classifiers=classifiers,
    install_requires=['jenkins-webapi'],
    py_modules=['bender_jenkins'],
    entry_points={
        'bender_script': [
            'jenkins = bender_jenkins:BenderJenkinsScript',
        ],
    }
)
