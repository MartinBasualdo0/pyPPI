from setuptools import setup, find_packages

# Leer las dependencias del archivo requirements.txt
with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='pyppi',
    version='1.0.0',
    author='MartinBasualdo0',
    author_email='martin.basualdo@hotmail.com',
    description='WebScrap de PortfolioPersonal',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/MartinBasualdo0/pyPPI',
    packages=find_packages(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    install_requires=required,
)
