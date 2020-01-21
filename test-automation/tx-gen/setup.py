import pathlib
from setuptools import setup

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

setup(
    name='harmony_transaction_generator',
    use_incremental=True,
    description="A transaction generator for the Harmony blockchain",
    long_description=README,
    long_description_content_type="text/markdown",
    author='Daniel Van Der Maden',
    author_email='daniel@harmony.one',
    url="http://harmony.one/",
    packages=['harmony_transaction_generator'],
    keywords=['Harmony', 'blockchain', 'protocol'],
    install_requires=[
        'pyhmy',
        'pytest',
        'pytest-ordering',
        'incremental',
        'click',
        'twisted',
        'requests'
    ],
    setup_requires=[
        'incremental',
        'click',
        'twisted',
        'pdoc3'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ]
)
