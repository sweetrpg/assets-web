from setuptools import setup

# Metadata goes in setup.cfg. These are here for GitHub's dependency graph.
setup(
    name="sweetrpg-assets-web",
    install_requires=[
        "analytics-python~=1.0",
        "blinker~=1.5",
        "Flask-Caching~=1.11",
        "Flask-CORS~=3.0",
        "Flask-DotEnv~=0.1",
        "Flask-Session~=0.4",
        "Flask~=3.0",
        "hiredis~=2.0",
        "python-dateutil~=2.8",
        "python-dotenv~=0.21",
        "python-editor~=1.0",
        "PyYAML~=6.0",
        "redis~=4.3",
        "requests~=2.28",
        "sentry-sdk[flask]~=1.28",
        "sweetrpg-web-core",
        "urllib3~=1.26",
    ],
    extras_require={},
)
