from pathlib import Path

from setuptools import setup, find_packages


def _read_version() -> str:
    namespace: dict[str, str] = {}
    version_file = Path(__file__).parent / "core" / "version.py"
    exec(version_file.read_text(encoding="utf-8"), namespace)
    return str(namespace["__version__"])

setup(
    name="secretloom",
    version=_read_version(),
    description="A private, local-first steganography and forensics workbench",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="SecretLoom contributors; based on StegoForge by Nour833",
    license="MIT",
    packages=find_packages(exclude=("tests", "tests.*")),
    include_package_data=False,
    package_data={
        "web": ["templates/*", "static/*"],
        "models": ["*.onnx"],
    },
    py_modules=["stegoforge"],
    python_requires=">=3.10",
    install_requires=(
        open("requirements.txt").read().splitlines() + 
        open("requirements-web.txt").read().splitlines()
    ),
    project_urls={
        "Source": "https://github.com/dlpwaters/secretloom",
        "Bug Tracker": "https://github.com/dlpwaters/secretloom/issues",
        "Upstream": "https://github.com/Nour833/StegoForge",
        "Changelog": "https://github.com/dlpwaters/secretloom/blob/main/CHANGELOG.md",
    },
    entry_points={
        "console_scripts": [
            "secretloom=stegoforge:app",
            "stegoforge=stegoforge:app",
        ]
    },
)
