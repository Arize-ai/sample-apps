from setuptools import setup, find_packages

# Read requirements
with open('requirements_simplified.txt') as f:
    requirements = f.read().splitlines()

setup(
    name="assurant-10k-chatbot",
    version="0.2.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=requirements,
)