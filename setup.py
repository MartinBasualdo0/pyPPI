import setuptools

with open("readme.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="py_ppi_arg",
    version="0.1.3",
    author="Martin Basualdo",
    author_email="martin.basualdo@hotmail.com",
    description="Python connector for PortfolioPersonals's Rest APIs.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MartinBasualdo0/pyPPI",
    packages=setuptools.find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'requests>=2.31.0',
        'simplejson>=3.19.1',
        'pyotp>=2.9.0',
        'cloudscraper>=1.2.71',
        'beautifulsoup4>=4.12.3',
        'bs4>=0.0.2'

    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Topic :: Office/Business :: Financial :: Investment",
        "Topic :: Software Development"
    ],
)