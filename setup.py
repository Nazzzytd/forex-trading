from setuptools import setup, find_packages

setup(
    name="forex_agent",
    version="1.0.0",
    description="UltraRAG Framework for Forex Trading Agent",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "pyyaml>=6.0",
        "python-dotenv>=1.0.0",
        "requests>=2.25.0",
        "pandas>=1.3.0",
    ],
    entry_points={
        'console_scripts': [
            'ultrarag=ultrarag.cli.main:main',
        ],
    },
    python_requires='>=3.8',
)