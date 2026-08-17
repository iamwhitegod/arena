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
    extras_require={
        "local": [
            "llama-cpp-python==0.3.34",
            "faster-whisper==1.2.1",
            "ctranslate2==4.8.1",
        ],
        "ollama": [
            "requests==2.34.2",
        ],
    },
    python_requires=">=3.10,<3.13",
    entry_points={
        "console_scripts": [
            "arena-engine=arena.main:main",
        ],
    },
)
