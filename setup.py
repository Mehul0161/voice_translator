from setuptools import setup, find_packages

setup(
    name="linguasync",
    version="1.0",
    packages=find_packages(),
    install_requires=[
        'kivy',
        'kivymd',
        'SpeechRecognition',
        'gtts',
        'deep-translator',
        'playsound==1.2.2',
        'requests'
    ],
) 