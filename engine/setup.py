from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="arena-engine",
    version="0.1.0",
    description="AI-powered video processing engine for Arena",
    author="",
    license="MIT",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "arena-engine=arena.main:main",
        ],
    },
)
