## [0.6.4] - 2026-08-08

### 🐛 Bug Fixes

- Load build info from build-info.json and set SCRIPT_NAME for url_for path generation

### ⚙️ Miscellaneous Tasks

- *(release)* Merge master into develop after v0.6.3
## [0.6.3] - 2026-08-08

### 🐛 Bug Fixes

- Move stray files to correct subdirectories
- Add comment headers to CSS files and revert test assertion
- Include template files in package manifest
- Correct template_folder path for blueprint

### 🚜 Refactor

- *(web)* Move hardcoded HTML templates to Jinja2 template files
- *(static)* Extract CSS to files and organize static assets by type

### 🧪 Testing

- Update static file paths to match new directory structure

### ⚙️ Miscellaneous Tasks

- *(release)* Merge master into develop after v0.6.2
## [0.6.2] - 2026-08-08

### ⚙️ Miscellaneous Tasks

- *(release)* Merge master into develop after v0.6.1
## [0.6.1] - 2026-08-08

### 🐛 Bug Fixes

- *(web)* Use url_for for static asset paths to support path prefixes

### ⚙️ Miscellaneous Tasks

- *(release)* Merge master into develop after v0.6.0
## [0.6.0] - 2026-08-08

### 🚀 Features

- *(avatar-menu)* Always-present menu shared assets - mystery-man icon, promote theme.js
- *(web)* Blueprint logo and dynamic platform link on front page
- *(assets)* Add a cover asset kind and cover-image CSS for catalog-web

### 🐛 Bug Fixes

- *(ci)* Scope Docker Build's concurrency group by ref
- *(kubernetes)* Make ArgoCD's per-release image tag override actually apply

### ⚙️ Miscellaneous Tasks

- *(release)* Merge master into develop after v0.5.0
## [0.5.0] - 2026-08-08

### 🚀 Features

- *(avatar-menu)* Support a Gravatar image with letter-avatar fallback

### 🐛 Bug Fixes

- *(ci)* Correct sweetrpg/kubernetes manifest path for update-deployment

### ⚙️ Miscellaneous Tasks

- *(release)* Merge master into develop after v0.4.1
## [0.4.1] - 2026-08-05

### ⚙️ Miscellaneous Tasks

- *(release)* Merge master into develop after v0.4.0
## [0.4.0] - 2026-08-05

### 🚀 Features

- *(assets-web)* Wire up AdminClient for admin-api integration
- *(assets-web)* Render a maintenance page during active maintenance mode
- *(static)* Add shared avatar-menu CSS/JS
- *(styles)* Add dark-theme variables and centralize shared component CSS
- *(branding)* Serve SVG logo variants for nav swap

### 🐛 Bug Fixes

- *(kubernetes)* Rename resources to namespace-scoped web-v1 convention

### 💼 Other

- Add admin-api-client.py git dependency

### ⚙️ Miscellaneous Tasks

- *(release)* Merge master into develop after v0.3.0
- Start work on #18 (suite-avatar-menu)
- Add SVG versions of site logo
## [0.3.0] - 2026-08-02

### 🚀 Features

- *(tooling)* Move to Python 3.14 and uv (#233)
- Add new images
- *(ci)* Add pytest-cov step summary, artifact upload (#249)
- *(ci)* Add warn-only coverage threshold check (79%) (#251)
- *(ci)* Add coverage badge, fix pre-existing broken badge link (#252)
- *(assets-web)* Style placeholder page with SweetRPG branding

### 🐛 Bug Fixes

- *(ci)* Docs job's uv install fails against a uv-managed Python (#234)
- *(ci)* Don't create a second venv on top of setup-uv's own (#235)
- *(ci)* Validate PRs into master too, not just develop (#238)
- Prefix the kind/id asset store with /asset (#239)
- Address CodeQL findings - workflow permissions, path injection (#242)
- *(k8s)* Remove HPA and PDB from dev overlay
- *(ci)* Host coverage badge on GitHub Pages, not a branch commit (#253)
- *(ci)* Filter tox exec noise out of the coverage badge percentage (#254)
- Volume mounts
- Namespace

### 🚜 Refactor

- Rename unused LIBRARY_API_BASE_URL constant to SHELF_API_BASE_URL (#259)

### 📚 Documentation

- *(k8s)* Point Ingress comment at main-web as DNS annotation owner (#250)

### ⚙️ Miscellaneous Tasks

- *(release)* Merge master into develop (one-time reconciliation)
- *(release)* Merge master into develop after v0.1.1
- *(release)* Merge master into develop after v0.2.0
- Remove replicas patch
- *(release)* Merge master into develop after v0.2.1
- Local (#257)
- Use default storage class for local
- Build arm64 image alongside amd64
- Fix memory spec
- Clean up files
- Remove NewRelic
- Update hostnames
- Update ingress config
- Update config
- *(kubernetes)* Move fully into sweetrpg-assets, own cache instance
## [0.2.1] - 2026-07-27

### 🚀 Features

- *(tooling)* Move to Python 3.14 and uv (#233)
- Add new images

### 🐛 Bug Fixes

- *(ci)* Docs job's uv install fails against a uv-managed Python (#234)
- *(ci)* Don't create a second venv on top of setup-uv's own (#235)
- *(ci)* Validate PRs into master too, not just develop (#238)
- Prefix the kind/id asset store with /asset (#239)
- Address CodeQL findings - workflow permissions, path injection (#242)
- *(k8s)* Scale replicas to 1 to relieve node disk pressure (#243)

### ⚙️ Miscellaneous Tasks

- *(release)* Merge master into develop (one-time reconciliation)
- *(release)* Merge master into develop after v0.1.1
- *(release)* Merge master into develop after v0.2.0
- Remove replicas patch
## [0.2.0] - 2026-07-27

### 🚀 Features

- *(tooling)* Move to Python 3.14 and uv (#233)
- Add new images

### 🐛 Bug Fixes

- *(ci)* Docs job's uv install fails against a uv-managed Python (#234)
- *(ci)* Don't create a second venv on top of setup-uv's own (#235)
- *(ci)* Validate PRs into master too, not just develop (#238)
- Prefix the kind/id asset store with /asset (#239)

### ⚙️ Miscellaneous Tasks

- *(release)* Merge master into develop (one-time reconciliation)
- *(release)* Merge master into develop after v0.1.1
## [0.1.1] - 2026-07-26

### 🚀 Features

- *(static)* Serve shared frontend static assets
- *(release)* Adopt the platform's real release workflow
- *(tooling)* Move to Python 3.14 and uv (#233)

### 🐛 Bug Fixes

- *(kubernetes)* Drop DestinationRule, no working Istio webhook for it
- *(kubernetes)* Add missing REDIS_HOST to the common ConfigMap
- *(kubernetes)* Add Ingress, drop unreachable LoadBalancer Service
- *(web)* Replace broken landing page with a real placeholder
- *(packaging)* Bundle static/ into built wheels via MANIFEST.in
- *(ci)* Docs job's uv install fails against a uv-managed Python (#234)
- *(ci)* Don't create a second venv on top of setup-uv's own (#235)
- *(kubernetes)* Drop DestinationRule from release
- *(kubernetes)* Add missing REDIS_HOST into release
- *(kubernetes)* Add Ingress into release
- *(web)* Landing page placeholder into release

### ⚙️ Miscellaneous Tasks

- *(release)* 0.1.0
- *(release)* Shared frontend static assets
- *(release)* Merge master into develop (one-time reconciliation)
## [0.1.0] - 2026-07-26

### 🚀 Features

- *(static)* Serve shared frontend static assets
- *(release)* Adopt the platform's real release workflow

### 🐛 Bug Fixes

- *(kubernetes)* Drop DestinationRule, no working Istio webhook for it
- *(kubernetes)* Add missing REDIS_HOST to the common ConfigMap
- *(kubernetes)* Add Ingress, drop unreachable LoadBalancer Service
- *(web)* Replace broken landing page with a real placeholder
- *(packaging)* Bundle static/ into built wheels via MANIFEST.in
# Changelog

<!--next-version-placeholder-->

## v0.0.31 (2022-07-31)


## v0.0.30 (2022-07-31)


## v0.0.29 (2022-07-30)


## v0.0.28 (2022-07-30)


## v0.0.27 (2022-01-15)


## v0.0.26 (2021-12-27)


## v0.0.25 (2021-12-11)


## v0.0.24 (2021-12-06)


## v0.0.23 (2021-11-13)


## v0.0.22 (2021-11-13)


## v0.0.21 (2021-11-13)


## v0.0.20 (2021-11-13)


## v0.0.19 (2021-11-13)


## v0.0.18 (2021-11-12)


## v0.0.17 (2021-11-12)


## v0.0.16 (2021-11-12)


## v0.0.15 (2021-11-12)


## v0.0.14 (2021-11-12)


## v0.0.13 (2021-11-11)


## v0.0.12 (2021-11-11)


## v0.0.11 (2021-11-11)


## v0.0.10 (2021-11-11)


## v0.0.9 (2021-11-11)


## v0.0.8 (2021-11-11)


## v0.0.7 (2021-11-11)


## v0.0.6 (2021-11-11)


## v0.0.5 (2021-11-11)


## v0.0.4 (2021-11-11)


## v0.0.3 (2021-11-11)


## v0.0.2 (2021-11-06)


## v0.0.1 (2021-11-04)

