#!/usr/bin/env python
import os
import subprocess
import sys
import contextlib
from distutils.command.build_ext import build_ext
from distutils.sysconfig import get_python_inc
import distutils.util
from distutils import ccompiler, msvccompiler
from setuptools import Extension, setup, find_packages

def is_new_osx():
    """Check whether we're on OSX >= 10.10"""
    name = distutils.util.get_platform()
    if sys.platform != "darwin":
        return False
    elif name.startswith("macosx-10"):
        minor_version = int(name.split("-")[1].split(".")[1])
        if minor_version >= 7:
            return True
        else:
            return False
    else:
        return False


PACKAGE_DATA = {'': ['*.pyx', '*.pxd']}
PACKAGES = find_packages()
MOD_NAMES = ['neuralcoref.neuralcoref']
COMPILE_OPTIONS = {
    "other": ["-O2", "-Wno-strict-prototypes", "-Wno-unused-function"],
}


LINK_OPTIONS = {"other": []}
if is_new_osx():
    # On Mac, use libc++ because Apple deprecated use of
    # libstdc
    COMPILE_OPTIONS["other"].append("-stdlib=libc++")
    LINK_OPTIONS["other"].append("-lc++")
    # g++ (used by unix compiler on mac) links to libstdc++ as a default lib.
    # See: https://stackoverflow.com/questions/1653047/avoid-linking-to-libstdc
    LINK_OPTIONS["other"].append("-nodefaultlibs")


# By subclassing build_extensions we have the actual compiler that will be used which is really known only after finalize_options
# http://stackoverflow.com/questions/724664/python-distutils-how-to-get-a-compiler-that-is-going-to-be-used
class build_ext_options:
    def build_options(self):
        for e in self.extensions:
            e.extra_compile_args += COMPILE_OPTIONS.get(
                self.compiler.compiler_type, COMPILE_OPTIONS["other"]
            )
        for e in self.extensions:
            e.extra_link_args += LINK_OPTIONS.get(
                self.compiler.compiler_type, LINK_OPTIONS["other"]
            )


class build_ext_subclass(build_ext, build_ext_options):
    def build_extensions(self):
        build_ext_options.build_options(self)
        build_ext.build_extensions(self)


@contextlib.contextmanager
def chdir(new_dir):
    old_dir = os.getcwd()
    try:
        os.chdir(new_dir)
        sys.path.insert(0, new_dir)
        yield
    finally:
        del sys.path[0]
        os.chdir(old_dir)


def generate_cython(root, source):
    print('Cythonizing sources')
    p = subprocess.call([sys.executable,
                         os.path.join(root, 'bin', 'cythonize.py'),
                         source], env=os.environ)
    if p != 0:
        raise RuntimeError('Running cythonize failed')


def setup_package():
    root = os.path.abspath(os.path.dirname(__file__))
    with chdir(root):

        generate_cython(root, 'neuralcoref')

        ext_modules = []
        for mod_name in MOD_NAMES:
            mod_path = mod_name.replace('.', '/') + '.cpp'
            extra_link_args = []
            if sys.platform == 'darwin':
                dylib_path = ['..' for _ in range(mod_name.count('.'))]
                dylib_path = '/'.join(dylib_path)
                dylib_path = '@loader_path/%s/neuralcoref/platform/darwin/lib' % dylib_path
                extra_link_args.append('-Wl,-rpath,%s' % dylib_path)
            ext_modules.append(
                Extension(mod_name, [mod_path],
                    language='c++', include_dirs=[get_python_inc(plat_specific=True)],
                    extra_link_args=extra_link_args))

        setup(name='neuralcoref',
            version='4.0',
            description="Coreference Resolution in spaCy with Neural Networks",
            url='https://github.com/huggingface/neuralcoref',
            author='Thomas Wolf',
            author_email='thomwolf@gmail.com',
            ext_modules=ext_modules,
            classifiers=[
                'Development Status :: 3 - Alpha',
                'Environment :: Console',
                'Intended Audience :: Developers',
                "Intended Audience :: Science/Research",
                "License :: OSI Approved :: MIT License",
                "Operating System :: POSIX :: Linux",
                "Operating System :: MacOS :: MacOS X",
                "Operating System :: Microsoft :: Windows",
                "Programming Language :: Cython",
                "Programming Language :: Python :: 3.6",
                "Programming Language :: Python :: 3.7",
                "Programming Language :: Python :: 3.8",
                "Topic :: Scientific/Engineering",
            ],
            install_requires=[
                "numpy>=1.15.0",
                "boto3",
                "requests>=2.13.0,<3.0.0",
                "spacy>=2.1.0"],
            setup_requires=['wheel', 'spacy>=2.1.0'],
            python_requires=">=3.6",
            packages=PACKAGES,
            package_data=PACKAGE_DATA,
            keywords='NLP chatbots coreference resolution',
            license='MIT',
            zip_safe=False,
            platforms='any',
            cmdclass={"build_ext": build_ext_subclass})

if __name__ == '__main__':
    setup_package()
