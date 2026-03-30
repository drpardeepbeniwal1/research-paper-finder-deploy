from setuptools import setup

setup(
    name="rpf-cli",
    version="1.0.0",
    py_modules=["openclaw_cli"],
    install_requires=["click>=8.0", "httpx>=0.28"],
    entry_points={"console_scripts": ["rpf=openclaw_cli:cli"]},
)
