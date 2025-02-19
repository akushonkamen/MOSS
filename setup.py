"""Moss项目安装配置"""
from setuptools import setup, find_packages

setup(
    name="mock_devices",
    version="0.1.0",
    description="Mock devices for testing and development",
    author="YP1017",
    package_dir={"": "mock_devices"},
    packages=find_packages(where="mock_devices"),
    install_requires=[
        "aiohttp>=3.8.0",
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "python-multipart>=0.0.5",
        "pydantic>=1.8.0",
        "asyncio>=3.4.3",
        "websockets>=10.0",
        "zeroconf>=0.38.0",
        "netifaces>=0.11.0",
    ],
    entry_points={
        'console_scripts': [
            'start-mock-devices=mock_devices.start_all_devices:main',
        ],
    },
    python_requires=">=3.8",
) 