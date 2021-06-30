# -*- coding:utf-8 -*-

from setuptools import setup

lint_deps = ["black==20.8b1", "mypy==0.790"]

extra_require = {
    "lint": lint_deps,
}

setup(
    name="echidna-parade",
    version="0.1",
    description="Meta-tool to test a contract with various configs, using Echidna processes",
    long_description_content_type="text/markdown",
    long_description=open("README.md").read(),
    packages=[
        "echidna_parade",
    ],
    license="AGPL3",
    entry_points="""
    [console_scripts]
    echidna-parade = echidna_parade.__main__:main
    """,
    keywords="echidna smart-contracts testing fuzzing swarm test-diversity",
    test_suite="nose.collector",
    tests_require=["nose"],
    classifiers=[
        "Intended Audience :: Developers",
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3",
    ],
    install_requires=["pyyaml", "slither-analyzer", "crytic-compile"],
    url="https://github.com/crytic/echidna-parade",
)
