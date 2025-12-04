# git-pm Comprehensive Documentation

This document addresses the key design decisions and workflows for git-pm.

## Table of Contents

1. [Repository URL Handling](#repository-url-handling)
2. [Consistent Code Usage](#consistent-code-usage)
3. [Local Development Workflow](#local-development-workflow)
4. [CI/CD Authentication](#cicd-authentication)
5. [Cache Management](#cache-management)
6. [Configuration System](#configuration-system)
7. [Conflict Resolution](#conflict-resolution)

---

## Repository URL Handling

### Problem

Different developers use different authentication methods:
- Developer A uses SSH: `git@github.com:company/repo.git`
- Developer B uses HTTPS: `https://github.com/company/repo.git`
- CI/CD uses HTTPS with token: `https://token@github.com/company/repo.git`

### Solution: Canonical Repository Identifiers

The manifest uses **canonical identifiers** that are independent of authentication:

```yaml
packages:
  utils:
    repo: github.com/company/monorepo  # Canonical form
    path: packages/utils
    ref:
      type: tag
      value: v1.2.0
```

The tool automatically resolves this to the appropriate URL based on:

1. **Environment variables** (highest priority)
2. **User/project configuration**
3. **Auto-detection** (SSH availability)
4. **Default fallback**

### URL Resolution Logic

```
Canonical: github.com/company/repo

↓

Check environment variable: GIT_PM_TOKEN_github_com
  If set → https://token@github.com/company/repo.git

↓

Check config for url_patterns:
  If pattern exists → Apply pattern

↓

Check config for git_protocol:
  If ssh → git@github.com:company/repo.git
  If https → https://github.com/company/repo.git

↓

Auto-detect SSH availability:
  Test: ssh -T git@github.com
  If works → git@github.com:company/repo.git
  Else → https://github.com/company/repo.git
```

### Examples

**Developer with SSH keys:**

```yaml
# ~/.git-pm/config.yaml
git_protocol:
  github.com: ssh
```

Result: `git@github.com:company/repo.git`

**Developer preferring HTTPS:**

```yaml
# ~/.git-pm/config.yaml
git_protocol:
  github.com: https
```

Result: `https://github.com/company/repo.git`

**CI/CD with token:**

```bash
export GIT_PM_TOKEN_github_com="ghp_abc123..."
python git-pm.py install
```

Result: `https://ghp_abc123...@github.com/company/repo.git`

### Benefits

✅ **Portable manifest** - Same git-pm.yaml works for everyone  
✅ **Developer choice** - Each developer uses their preferred method  
✅ **CI/CD friendly** - Easy token injection  
✅ **Consistent caching** - Cache key uses canonical form  

---

## Consistent Code Usage

### Problem

Code needs to work the same way regardless of how git URLs are configured.

### Solution: Stable Package Names

The package **name** in the manifest becomes the directory name in `.git-packages/`:

```yaml
packages:
  utils:          # ← This becomes .git-packages/utils/
    repo: github.com/company/monorepo
    path: packages/utils
```

Your code always imports from the same location:

```python
# Always works the same way
import sys
sys.path.insert(0, '.git-packages')

from utils import helper
from components import Button
```

### Directory Structure

```
your-project/
├── git-pm.yaml
├── .git-packages/
│   ├── utils/           → symlink to cache
│   ├── components/      → symlink to cache
│   └── data-models/     → symlink to cache
└── src/
    └── main.py          # Imports from .git-packages/
```

The git URL configuration is **completely transparent** to your code.

### Benefits

✅ **No code changes** needed when switching auth methods  
✅ **Consistent imports** across team  
✅ **Easy to reason about** - package name = directory name  

---

## Local Development Workflow

### Problem

Developers need to work on uncommitted changes to packages without breaking the workflow.

### Solution: Local Override System

#### Step 1: Create `git-pm.local.yaml`

```yaml
overrides:
  utils:
    type: local
    path: ../monorepo-local/packages/utils
```

**Important:** Add to `.gitignore`:

```gitignore
git-pm.local.yaml
```

#### Step 2: Run Install

```bash
python git-pm.py install
```

The tool will:
1. Load `git-pm.yaml` (base manifest)
2. Load `git-pm.local.yaml` (your overrides)
3. Merge configurations
4. Create symlink to local path instead of cache

#### Step 3: Make Changes

Your local changes are immediately reflected:

```
.git-packages/utils → /home/you/workspace/monorepo-local/packages/utils
```

Edit files in `monorepo-local/packages/utils/`, and they're instantly available in your project.

### Workflow Examples

**Scenario A: Fixing a bug in a dependency**

```bash
# 1. Clone the dependency locally
git clone git@github.com:company/monorepo.git ~/workspace/monorepo-local

# 2. Create override
cat > git-pm.local.yaml << EOF
overrides:
  utils:
    type: local
    path: ~/workspace/monorepo-local/packages/utils
EOF

# 3. Install (uses local version)
python git-pm.py install

# 4. Make changes
cd ~/workspace/monorepo-local/packages/utils
# Edit files...

# 5. Test in your project
cd ~/your-project
python test.py  # Uses local version

# 6. When done, commit to monorepo and remove override
rm git-pm.local.yaml
python git-pm.py install  # Back to git version
```

**Scenario B: Developing a new package**

```yaml
# git-pm.yaml - Add your new package
packages:
  my-new-feature:
    type: local
    path: ../my-new-feature
```

No override needed - local packages can be in the main manifest during development.

### Multiple Overrides

You can override multiple packages:

```yaml
overrides:
  utils:
    type: local
    path: ../monorepo-local/packages/utils
  
  components:
    type: local
    path: ../monorepo-local/packages/components
  
  data-models:
    type: local
    path: /absolute/path/to/data-models
```

### Benefits

✅ **Non-invasive** - No changes to main manifest  
✅ **Flexible** - Override any or all packages  
✅ **Immediate feedback** - Changes instantly available  
✅ **No commits needed** - Test before committing  

---

## CI/CD Authentication

### Problem

CI/CD pipelines need secure authentication without hardcoding credentials.

### Solution: Environment Variable Tokens

#### Token Format

```bash
GIT_PM_TOKEN_{domain}="token_value"
```

The domain is normalized: dots become underscores.

- `github.com` → `GIT_PM_TOKEN_github_com`
- `dev.azure.com` → `GIT_PM_TOKEN_dev_azure_com`
- `gitlab.internal.company` → `GIT_PM_TOKEN_gitlab_internal_company`

#### GitHub Actions Example

```yaml
name: Build

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        env:
          GIT_PM_TOKEN_github_com: ${{ secrets.GITHUB_TOKEN }}
        run: |
          python git-pm.py install
      
      - name: Run tests
        run: python -m pytest
```

#### Azure DevOps Example

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: '3.9'
  
  - script: |
      python git-pm.py install
    displayName: 'Install dependencies'
    env:
      GIT_PM_TOKEN_dev_azure_com: $(System.AccessToken)
  
  - script: |
      python -m pytest
    displayName: 'Run tests'
```

#### GitLab CI Example

```yaml
stages:
  - build
  - test

build:
  stage: build
  script:
    - export GIT_PM_TOKEN_gitlab_com="$CI_JOB_TOKEN"
    - python git-pm.py install
  artifacts:
    paths:
      - .git-packages/

test:
  stage: test
  script:
    - python -m pytest
  dependencies:
    - build
```

### Domain-Specific Token Configuration

For multiple git providers:

```bash
# Set multiple tokens
export GIT_PM_TOKEN_github_com="ghp_..."
export GIT_PM_TOKEN_gitlab_com="glpat_..."
export GIT_PM_TOKEN_dev_azure_com="pat_..."

# Install
python git-pm.py install
```

### Config File with Environment Variables

Avoid hardcoding tokens:

```yaml
# ~/.git-pm/config.yaml
credentials:
  github.com:
    token: ${GITHUB_TOKEN}
  
  dev.azure.com:
    token: ${ADO_PAT}
  
  gitlab.internal.company:
    token: ${GITLAB_TOKEN}
```

Then set environment variables:

```bash
export GITHUB_TOKEN="ghp_..."
export ADO_PAT="..."
export GITLAB_TOKEN="glpat_..."
```

### Benefits

✅ **No secrets in code** - Tokens from environment  
✅ **Platform native** - Uses platform secret management  
✅ **Per-domain tokens** - Different tokens for different services  
✅ **Easy rotation** - Update in CI/CD settings  

---

## Cache Management

### Cache Structure

```
~/.cache/git-pm/
└── objects/
    ├── 7f3a2b1c9d8e6f4a/   # Hash of (repo + ref + path)
    │   ├── .git/
    │   └── packages/
    │       └── utils/
    └── abc123def456/
        ├── .git/
        └── components/
```

### Cache Key Generation

Cache key = `SHA256(repo + ref_type + ref_value + path)[:16]`

Example:

```python
repo = "github.com/company/monorepo"
ref_type = "tag"
ref_value = "v1.0.0"
path = "packages/utils"

key = SHA256(
    "github.com/company/monorepo#tag:v1.0.0#packages/utils"
)[:16]
# → "7f3a2b1c9d8e6f4a"
```

### Cache Behavior

**Tags and Commits (Immutable):**
- Cached once
- Never updated
- Always reused

**Branches (Mutable):**
- Cached on first install
- Updated on install (if `auto_update_branches: true`)
- Explicitly updated via `update` command

### Multiple Versions

You can have multiple versions of the same package cached:

```yaml
packages:
  utils-stable:
    repo: github.com/company/monorepo
    path: packages/utils
    ref:
      type: tag
      value: v1.0.0
  
  utils-latest:
    repo: github.com/company/monorepo
    path: packages/utils
    ref:
      type: branch
      value: main
```

Cache will have two entries:
- `7f3a2b1c...` (tag:v1.0.0)
- `abc123de...` (branch:main)

### Cache Cleanup

Manual cleanup:

```bash
# Remove installed packages only
python git-pm.py clean

# Remove installed packages and cache
python git-pm.py clean --cache
```

The cache is safe to delete - it will be repopulated on next install.

---

## Configuration System

### Three-Level Hierarchy

```
User Config (lowest priority)
    ~/.git-pm/config.yaml

        ↓ (merged)

Project Config (overrides user)
    .git-pm/config.yaml

        ↓ (merged)

Environment Variables (highest priority)
    GIT_PM_*
```

### User-Level Config

Location: `~/.git-pm/config.yaml`

Purpose: Personal preferences for all projects

Example:

```yaml
# My preferred defaults
cache_dir: ~/.cache/git-pm
packages_dir: .git-packages

git_protocol:
  github.com: ssh
  gitlab.com: ssh

credentials:
  dev.azure.com:
    token: ${ADO_PAT}
```

### Project-Level Config

Location: `.git-pm/config.yaml`

Purpose: Project-specific settings (team can decide to commit or not)

Example:

```yaml
# Force HTTPS for this project
git_protocol:
  github.com: https

# Custom package directory
packages_dir: .packages

# Disable auto-update
auto_update_branches: false
```

### Environment Variables

Purpose: Override anything, primarily for CI/CD

Available variables:

```bash
# Authentication tokens
GIT_PM_TOKEN_{domain}="token"

# Package overrides
GIT_PM_OVERRIDE_{package}="/path"

# Config overrides (future)
GIT_PM_CACHE_DIR="/custom/cache"
GIT_PM_PACKAGES_DIR=".custom-packages"
```

### Configuration Precedence Example

**User config:**
```yaml
packages_dir: .my-packages
auto_update_branches: true
git_protocol:
  github.com: ssh
```

**Project config:**
```yaml
packages_dir: .git-packages
git_protocol:
  github.com: https
```

**Result:**
- `packages_dir`: `.git-packages` (project overrides user)
- `auto_update_branches`: `true` (from user, not overridden)
- `git_protocol.github.com`: `https` (project overrides user)

---

## Conflict Resolution

### Strategy: Explicit Versioning

git-pm uses a **flat structure with explicit versions** (Strategy 1 from design).

### No Automatic Resolution

If two packages need different versions, you must explicitly decide:

```yaml
packages:
  # Use two different names for different versions
  utils-v1:
    repo: github.com/company/monorepo
    path: packages/utils
    ref:
      type: tag
      value: v1.0.0
  
  utils-v2:
    repo: github.com/company/monorepo
    path: packages/utils
    ref:
      type: tag
      value: v2.0.0
```

Result:
```
.git-packages/
├── utils-v1/  (version 1.0.0)
└── utils-v2/  (version 2.0.0)
```

### Rationale

✅ **Explicit** - No hidden version resolution  
✅ **Predictable** - You control what's installed  
✅ **Simple** - No complex dependency solver  
✅ **Debuggable** - Clear what version is used  

### Best Practices

1. **Use tags for production**
   ```yaml
   ref:
     type: tag
     value: v1.2.0
   ```

2. **Use branches for development**
   ```yaml
   ref:
     type: branch
     value: main
   ```

3. **Pin commits for absolute stability**
   ```yaml
   ref:
     type: commit
     value: abc123def456...
   ```

4. **Name packages clearly**
   ```yaml
   packages:
     utils-stable:  # Clear which version
       ref:
         type: tag
         value: v1.0.0
   ```

---

## Summary

This documentation addresses all major design concerns:

1. ✅ **Different git URLs** - Canonical identifiers + resolution
2. ✅ **Consistent usage** - Stable package names
3. ✅ **Local development** - Override system
4. ✅ **CI/CD auth** - Environment variable tokens
5. ✅ **Cache management** - Hash-based, efficient
6. ✅ **Configuration** - Three-level hierarchy
7. ✅ **Conflicts** - Explicit versioning

The system is designed to be **simple**, **predictable**, and **flexible**.
