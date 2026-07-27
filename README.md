# Assets web

[![Unit tests](https://github.com/sweetrpg/assets-web/actions/workflows/python-ci.yml/badge.svg)](https://github.com/sweetrpg/assets-web/actions/workflows/python-ci.yml)
[![Coverage](https://github.com/sweetrpg/assets-web/blob/develop/coverage.svg)](https://github.com/sweetrpg/assets-web)
[![License](https://img.shields.io/github/license/sweetrpg/assets-web.svg)](https://img.shields.io/github/license/sweetrpg/assets-web.svg)
[![Issues](https://img.shields.io/github/issues/sweetrpg/assets-web.svg)](https://img.shields.io/github/issues/sweetrpg/assets-web.svg)
[![PRs](https://img.shields.io/github/issues-pr/sweetrpg/assets-web.svg)](https://img.shields.io/github/issues-pr/sweetrpg/assets-web.svg)
[![Dependabot](https://badgen.net/github/dependabot/sweetrpg/assets-web)](https://badgen.net/github/dependabot/sweetrpg/assets-web)

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
[![Built with love](https://ForTheBadge.com/images/badges/built-with-love.svg)](https://ForTheBadge.com/images/badges/built-with-love.svg)

Flask service that stores and serves the SweetRPG platform's binary assets (avatars, maps,
tokens, portraits) - `GET /asset/<kind>/<id>` fetches one, `POST /asset/<kind>/<id>`
(authenticated) uploads one. Files live on a shared `ReadWriteMany` volume; reads are cached in
Redis.

## Documentation

Documentation for this package can be found [here](https://sweetrpg.github.io/assets-web).
