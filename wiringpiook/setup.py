"""
   Python C Extension Module WiringPi OOK

   Send OOK pulse train to digital GPIO using wiringPi C library

   See: https://github.com/latchdevel/raspicode

   Copyright (c) 2022-2024 Jorge Rivera. All right reserved.
   License GNU Lesser General Public License v3.0.
"""

from setuptools import setup, Extension

setup(
    name="wiringpiook",
    version="1.1",
    ext_modules=[Extension('wiringpiook', ['wiringpiook.c','wiringPi.c'])],
    url="https://github.com/latchdevel/raspicode",
    author="Jorge Rivera",
    author_email="latchdevel@users.noreply.github.com",
    description='Python C Extension Module to send OOK pulse train to digital gpio using wiringPi library',
    keywords="wiringpiook, wiringpi, ook, picode, module, extension, 315Mhz, 433Mhz, gpio, raspberry",
    license='LGPL-3.0',
    classifiers=[ # https://pypi.org/pypi?%3Aaction=list_classifiers
        "License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)",
        "Programming Language :: C",
        "Programming Language :: Python",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Development Status :: 4 - Beta"
    ]
)