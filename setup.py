from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ofcli",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="OmniFocus CLI - Command-line interface for OmniFocus with AI integration",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/omni-cli",
    packages=find_packages(),
    py_modules=["ofcli", "utils"],
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
    ],
    python_requires=">=3.9",
    install_requires=[
        "openai>=1.0.0",
        "anthropic>=0.3.1",
        "requests>=2.28.0",
        "typer[all]>=0.6.1",
        "python-dotenv>=1.0.0",
        "dateparser>=1.1.0",
        "rich>=13.5.2",
        "loguru>=0.6.0",
        "appscript>=1.2.5",
    ],
    entry_points={
        "console_scripts": [
            "ofcli=ofcli:app",
        ],
    },
) 