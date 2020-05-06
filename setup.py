#!/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

def parse_requirements(requirements):
  with open(requirements) as reqf:
    items = [line.strip("\n") for line in reqf if not line.startswith("#")]
    return list(filter(lambda s: s.strip() != "", items))

setup(
  name="hachiko-bapu", version="0.1.7",
  python_requires=">=3.5",
  author="duangsuse", author_email="fedora-opensuse@outlook.com",
  url="https://github.com/duangsuse-valid-projects/Hachiko",
  description="Simple pygame GUI tool for creating pitch timeline",
  long_description="""
Simple tool for creating pitch timeline, this program divides midi creation into pitches and timeline part.

When creating timeline, press A to give position/duration information, and use S to split different notes directly when holding A.

This program requires system FluidSynth library to run, this package also provides command utility srt2mid and lrc_merge.
""",
  classifiers=[
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Topic :: Multimedia",
    "Topic :: Multimedia :: Sound/Audio",
    "Topic :: Utilities"
  ],

  packages=find_packages(),
  package_data={ "": ["*.sf2"] },
  install_requires=parse_requirements("requirements.txt"),
  extras_require={
    "synthesize buffer": ["numpy>=1.0"],
    "funutils codegen": ["pyparsing>=2.4"]
  },
  entry_points={
    "console_scripts": [
      "hachiko = hachiko_bapu.hachi:main",
      "srt2mid = hachiko_bapu.cli_tools.srt2mid:main",
      "lrc_merge = hachiko_bapu.cli_tools.lrc_merge:main"
    ]
  })
