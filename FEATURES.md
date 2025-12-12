# git-pm Features - Complete Guide

## 📋 Feature Index

### Core Features (v0.1.0)
1. [Full Dependency Resolution](#full-dependency-resolution)
2. [Explicit Versioning](#explicit-versioning)
3. [Branch Auto-Resolution](#branch-auto-resolution)
4. [Independent Versioning](#independent-versioning)
5. [Git Sparse-Checkout](#git-sparse-checkout)
6. [Smart Caching](#smart-caching)
7. [Cross-Platform Support](#cross-platform-support)
8. [Azure DevOps Integration](#azure-devops-integration)

### New Features (v0.2.0)
9. [Nested Dependency Symlinks](#nested-dependency-symlinks)
10. [Environment Variables Generation](#environment-variables-generation)
11. [Windows Symlink Support](#windows-symlink-support)
12. [Automatic .gitignore Management](#automatic-gitignore-management)
13. [Local Override Discovery](#local-override-discovery)
14. [Path Resolution](#path-resolution)

---

## Core Features

### Full Dependency Resolution

**What it does:** Automatically discovers and installs all nested dependencies recursively.

**Example:**
```yaml
# Your git-pm.yaml
packages:
  my-app:
    repo: github.com/company/repo
    path: app
    ref:
      type: tag
      value: v1.0.0

# my-app/git-pm.yaml (nested)
packages:
  utils:
    repo: github.com/company/shared
    path: utils
    ref:
      type: tag
      value: v2.0.0
  
  config:
    repo: github.com/company/shared
    path: config
    ref:
      type: tag
      value: v1.5.0
```

**Result:**
```bash
$ git-pm install
🔍 Discovering dependencies...
📦 Discovering my-app...
  Found 2 dependencies
📦 Discovering utils (depth 1)...
📦 Discovering config (depth 1)...
   Found 3 total packages
📦 Planning installation order...
   Order: utils -> config -> my-app
📥 Installing 3 package(s)...
```

**Benefits:**
- ✅ No manual dependency tracking
- ✅ Transitive dependencies resolved
- ✅ Topological sorting (dependencies install first)
- ✅ Circular dependency detection

**Disable:** Use `--no-resolve-deps` for flat install

---

### Explicit Versioning

**What it does:** Uses exact references (tag/branch/commit), no version ranges.

**Supported reference types:**
```yaml
# Tag (recommended for releases)
ref:
  type: tag
  value: v1.0.0

# Branch (for active development)
ref:
  type: branch
  value: main

# Commit SHA (for precise control)
ref:
  type: commit
  value: abc123def456
```

**Benefits:**
- ✅ No version conflicts
- ✅ Reproducible builds
- ✅ Clear intent (exact versions)
- ✅ Works with any git ref

**Comparison with other tools:**

| Tool | Version Format | Example |
|------|----------------|---------|
| npm | Range | `^1.0.0` (1.0.0 - 2.0.0) |
| pip | Range | `>=1.0.0,<2.0.0` |
| **git-pm** | **Explicit** | `v1.0.0` (exact) |

---

### Branch Auto-Resolution

**What it does:** Automatically resolves branch names to latest commit SHA.

**Example:**
```yaml
packages:
  dev-tools:
    repo: github.com/company/tools
    path: tools
    ref:
      type: branch
      value: develop  # Branch name
```

**During install:**
```bash
📦 Discovering dev-tools...
  Resolving branch 'develop'...
  Resolved to commit: abc123def456
```

**Lockfile:**
```json
{
  "packages": {
    "dev-tools": {
      "type": "git",
      "repo": "https://github.com/company/tools",
      "path": "tools",
      "ref_type": "commit",
      "ref_value": "abc123def456",
      "original_ref": {
        "type": "branch",
        "value": "develop"
      }
    }
  }
}
```

**Update branches:**
```bash
$ git-pm update
🔄 git-pm update
📦 Updating dev-tools...
  Branch: develop
  Old commit: abc123
  New commit: xyz789
  ✓ Updated
```

**Benefits:**
- ✅ Deterministic installs (same commit for same branch)
- ✅ Can update to latest with `git-pm update`
- ✅ All developers get same code
- ✅ Lockfile tracks exact commit

---

### Independent Versioning

**What it does:** Each package can be at a different version/commit.

**Example:**
```yaml
packages:
  utils-stable:
    repo: github.com/company/shared
    path: utils
    ref:
      type: tag
      value: v1.0.0  # Stable release

  utils-beta:
    repo: github.com/company/shared
    path: utils
    ref:
      type: tag
      value: v2.0.0-beta  # Beta testing

  utils-dev:
    repo: github.com/company/shared
    path: utils
    ref:
      type: branch
      value: develop  # Latest development
```

**Result:**
```
.git-packages/
├── utils-stable/   (v1.0.0)
├── utils-beta/     (v2.0.0-beta)
└── utils-dev/      (develop branch)
```

**Use case:**
```hcl
# Terraform - testing migration
module "production" {
  source = "./.git-packages/utils-stable"
}

module "staging" {
  source = "./.git-packages/utils-beta"
}
```

---

### Git Sparse-Checkout

**What it does:** Only clones specific directories from monorepos.

**Example monorepo:**
```
monorepo/
├── packages/
│   ├── auth/        (100 MB)
│   ├── database/    (200 MB)
│   └── utils/       (50 MB)
├── services/
│   ├── api/         (500 MB)
│   └── web/         (800 MB)
└── docs/            (300 MB)
```

**git-pm.yaml:**
```yaml
packages:
  utils:
    repo: github.com/company/monorepo
    path: packages/utils  # Only this directory
    ref:
      type: tag
      value: v1.0.0
```

**Result:**
- ✅ Downloads: 50 MB (utils only)
- ❌ Without sparse: 1.95 GB (entire repo)

**Performance:**

| Operation | Full Clone | Sparse Checkout |
|-----------|------------|-----------------|
| Initial | 5 min | 10 sec |
| Disk Usage | 2 GB | 50 MB |
| Network | 2 GB | 50 MB |

---

### Smart Caching

**What it does:** Caches cloned repositories for fast repeated installs.

**Cache location:** `.git-pm-cache/` (in project root)

**Cache key generation:**
```python
cache_key = sha256(f"{repo}:{path}:{ref_type}:{ref_value}")[:16]
```

**Example:**
```bash
# First install
$ git-pm install
📦 Installing utils...
  Cloning github.com/company/repo...
  ✓ Copied: utils -> .git-packages/utils
Time: 10 seconds

# Second install (after clean)
$ git-pm clean && git-pm install
📦 Installing utils...
  Found in cache: a1b2c3d4e5f6g7h8
  ✓ Copied: utils -> .git-packages/utils
Time: 0.5 seconds
```

**Cache behavior:**

| Reference Type | Caching |
|----------------|---------|
| Tag | Permanent (tags don't change) |
| Commit | Permanent (commits immutable) |
| Branch | Refresh on install (branches change) |

**Cache management:**
```bash
# View cache
ls -lh .git-pm-cache/

# Clean cache (keeps .git-packages)
rm -rf .git-pm-cache/

# Full clean (removes packages and cache)
git-pm clean
```

---

### Cross-Platform Support

**What it does:** Works on Linux, macOS, and Windows with platform-specific adaptations.

**Platform differences:**

| Feature | Linux/macOS | Windows |
|---------|-------------|---------|
| Symlinks | Native | Developer Mode or junctions |
| Line endings | LF | CRLF (git handles) |
| Paths | `/` | `\` (Python handles) |
| Scripts | `.sh` | `.bat` / `.ps1` |
| Encoding | UTF-8 | UTF-8 (forced) |

**Windows-specific features:**

1. **Encoding fix:** Forces UTF-8 output for emojis (🚀 ✓ ✗)
2. **Read-only handling:** Removes read-only flag before deletion
3. **Junction fallback:** Auto-uses junctions if symlinks unavailable
4. **Batch wrapper:** Creates `.bat` file for command access

**Installation:**
```bash
# Linux/macOS
~/.local/bin/git-pm
~/.local/bin/git-pm.py

# Windows
%USERPROFILE%\.git-pm\git-pm.bat
%USERPROFILE%\.git-pm\git-pm.py
```

---

### Azure DevOps Integration

**What it does:** Built-in Personal Access Token (PAT) injection for Azure DevOps.

**Usage:**
```bash
# Set PAT token
export AZURE_DEVOPS_PAT="your-token-here"

# git-pm automatically injects it
git-pm install
```

**How it works:**
```python
# Automatic URL rewriting
# From: dev.azure.com/org/project/_git/repo
# To:   https://PAT@dev.azure.com/org/project/_git/repo
```

**Supported formats:**
```yaml
# Format 1: Full URL
repo: https://dev.azure.com/org/project/_git/repo

# Format 2: Short form (recommended)
repo: dev.azure.com/org/project/_git/repo

# Format 3: SSH (uses your SSH keys)
repo: git@ssh.dev.azure.com:v3/org/project/repo
```

**CI/CD integration:**
```yaml
# GitHub Actions
- name: Install dependencies
  env:
    AZURE_DEVOPS_PAT: ${{ secrets.AZURE_DEVOPS_PAT }}
  run: git-pm install

# Azure Pipelines
- script: git-pm install
  env:
    AZURE_DEVOPS_PAT: $(System.AccessToken)
```

---

## New Features (v0.2.0)

### Nested Dependency Symlinks

**What it does:** Automatically creates `.git-packages/` inside each package with symlinks to its dependencies.

**Problem solved:**
```
# Development
workspace/packageB/main.tf needs: ../.git-packages/packageA

# Consumption
projectC/.git-packages/packageB/main.tf needs: ../packageA

# No single path works in both! ❌
```

**Solution:**
```
projectC/.git-packages/packageB/.git-packages/packageA → ../../packageA
```

**Your code (works everywhere):**
```hcl
# packageB/main.tf
module "dependency" {
  source = ".git-packages/packageA"  # Works in both scenarios!
}
```

**Installation:**
```bash
$ git-pm install
...
🔗 Creating dependency symlinks...
  ✓ packageB/packageA -> packageA
  ✓ packageB/packageC -> packageC
```

**See:** [NESTED_DEPENDENCY_SYMLINKS.md](NESTED_DEPENDENCY_SYMLINKS.md)

---

### Environment Variables Generation

**What it does:** Generates `.git-pm.env` with absolute paths for use in scripts.

**Generated file:**
```bash
# .git-pm.env
export GIT_PM_PACKAGES_DIR="/absolute/path/to/.git-packages"
export GIT_PM_PROJECT_ROOT="/absolute/path/to/project"
export GIT_PM_PACKAGE_PACKAGEA="/absolute/path/to/.git-packages/packageA"
```

**Usage examples:**

**Bash:**
```bash
#!/bin/bash
source .git-pm.env
terraform -chdir="$GIT_PM_PACKAGE_PACKAGEB" apply
```

**Python:**
```python
import os
pkg_dir = os.environ['GIT_PM_PACKAGES_DIR']
```

**Makefile:**
```makefile
include .git-pm.env

deploy:
	cd $(GIT_PM_PACKAGE_PACKAGEB) && terraform apply
```

**Node.js:**
```javascript
require('dotenv').config({ path: '.git-pm.env' });
const pkgPath = process.env.GIT_PM_PACKAGE_PACKAGEA;
```

**See:** [ENVIRONMENT_VARIABLES_GUIDE.md](ENVIRONMENT_VARIABLES_GUIDE.md)

---

### Windows Symlink Support

**What it does:** Automatically handles Windows symlinks with intelligent fallback to junction points.

**Three scenarios:**

1. **Developer Mode Enabled:** Creates true symlinks (recommended)
2. **No Developer Mode:** Auto-falls back to junction points (works identically)
3. **Fallback Failed:** Use environment variables instead

**Output examples:**

**Scenario 1:**
```bash
🔗 Creating dependency symlinks...
  ✓ packageB/packageA -> packageA
```

**Scenario 2:**
```bash
🔗 Creating dependency symlinks...
  ⚠️  Windows: Symlinks require Developer Mode
     Falling back to junction points...
  ✓ packageB/packageA -> packageA (junction)
```

**Enable Developer Mode:**
```
Settings → Update & Security → For developers → Developer Mode ON
```

**Both work identically with Terraform!**

**See:** [WINDOWS_SYMLINK_SUPPORT.md](WINDOWS_SYMLINK_SUPPORT.md)

---

### Automatic .gitignore Management

**What it does:** Automatically adds git-pm files to `.gitignore` on every install.

**Added entries:**
```gitignore
# git-pm - Package manager files
.git-packages/
.git-pm.env
git-pm.local.yaml
git-pm.lock
```

**Installation:**
```bash
$ git-pm install
📝 Updating .gitignore...
  ✓ Added: .git-packages/
  ✓ Added: .git-pm.env
  ✓ Added: git-pm.local.yaml
  ✓ Added: git-pm.lock
```

**Smart behavior:**
- ✅ Creates .gitignore if missing
- ✅ Never duplicates entries
- ✅ Preserves existing structure
- ✅ Detects trailing slash variants

**Skip:**
```bash
git-pm install --no-gitignore
```

**Why ignore:**
- `.git-packages/` → 100+ MB, like node_modules
- `.git-pm.env` → Absolute paths (per-developer)
- `git-pm.local.yaml` → Local overrides (machine-specific)
- `git-pm.lock` → Optional (apps commit, libraries ignore)

**See:** [GITIGNORE_MANAGEMENT.md](GITIGNORE_MANAGEMENT.md)

---

### Local Override Discovery

**What it does:** Checks local overrides BEFORE cloning from remote repositories.

**Benefits:**
- ✅ No remote clones for overridden packages
- ✅ 6x faster installation
- ✅ Works offline
- ✅ Reads nested dependencies from local path

**git-pm.local.yaml:**
```yaml
overrides:
  my-package:
    type: local
    path: ../local-dev/my-package
```

**Installation (before fix):**
```bash
📦 Discovering my-package...
  Cloning github.com/company/repo...  ❌ Unnecessary!
📦 Installing my-package...
  Override: my-package -> local
```

**Installation (after fix):**
```bash
📦 Discovering my-package...
  Using local override: ../local-dev/my-package  ✅ No clone!
📦 Installing my-package...
  Override: my-package -> local (symlinked)
```

**See:** [LOCAL_OVERRIDE_DISCOVERY_FIX.md](LOCAL_OVERRIDE_DISCOVERY_FIX.md)

---

### Path Resolution

**What it does:** Solves the path conflict between development and consumption using two complementary approaches.

**The problem:**
- Development: `../.git-packages/packageA` ✅
- Consumption: `../packageA` ✅
- No single path works! ❌

**Solution 1: Symlinks (for Terraform)**
```
.git-packages/packageB/.git-packages/packageA → ../../packageA
```

**Solution 2: Environment variables (for scripts)**
```bash
source .git-pm.env
echo $GIT_PM_PACKAGE_PACKAGEA  # Absolute path
```

**Your code:**
```hcl
# Change from:
source = "../.git-packages/packageA"  ❌

# To:
source = ".git-packages/packageA"  ✅ Works everywhere!
```

**See:** [PATH_RESOLUTION_COMPLETE_GUIDE.md](PATH_RESOLUTION_COMPLETE_GUIDE.md)

---

## Feature Comparison

### vs npm/yarn

| Feature | npm/yarn | git-pm |
|---------|----------|--------|
| Dependency resolution | ✅ | ✅ |
| Version ranges | ✅ | ❌ (explicit only) |
| Monorepo support | Workspaces | Sparse-checkout |
| Local development | `npm link` | Automatic symlinks |
| Platform | Node.js | Any (git) |
| Language | JavaScript | Any |

### vs pip

| Feature | pip | git-pm |
|---------|-----|--------|
| Dependency resolution | ✅ | ✅ |
| Git repositories | Limited | Native |
| Monorepo support | ❌ | ✅ |
| Version ranges | ✅ | ❌ (explicit only) |
| Platform | Python | Any (git) |
| Language | Python | Any |

### vs git submodules

| Feature | Submodules | git-pm |
|---------|------------|--------|
| Dependency resolution | ❌ | ✅ |
| Version pinning | Commit only | Tag/Branch/Commit |
| Nested dependencies | Manual | Automatic |
| Monorepo support | Full clone | Sparse-checkout |
| Update command | Complex | Simple |
| .gitmodules | Required | Not needed |

---

## Documentation Index

### Getting Started
- [README.md](README.md) - Main documentation
- [DEPENDENCY_RESOLUTION.md](DEPENDENCY_RESOLUTION.md) - How dependency resolution works

### Feature Documentation
- [NESTED_DEPENDENCY_SYMLINKS.md](NESTED_DEPENDENCY_SYMLINKS.md) - Symlink implementation
- [ENVIRONMENT_VARIABLES_GUIDE.md](ENVIRONMENT_VARIABLES_GUIDE.md) - Using .git-pm.env
- [WINDOWS_SYMLINK_SUPPORT.md](WINDOWS_SYMLINK_SUPPORT.md) - Windows compatibility
- [GITIGNORE_MANAGEMENT.md](GITIGNORE_MANAGEMENT.md) - Automatic .gitignore
- [LOCAL_OVERRIDE_DISCOVERY_FIX.md](LOCAL_OVERRIDE_DISCOVERY_FIX.md) - Local overrides
- [PATH_RESOLUTION_COMPLETE_GUIDE.md](PATH_RESOLUTION_COMPLETE_GUIDE.md) - Path resolution

### CI/CD & Deployment
- [CI_CD_DOCUMENTATION.md](CI_CD_DOCUMENTATION.md) - CI/CD integration
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deployment instructions

### Troubleshooting
- [WINDOWS_QUICK_GUIDE.md](WINDOWS_QUICK_GUIDE.md) - Windows quick reference
- [GITIGNORE_QUICK_REFERENCE.md](GITIGNORE_QUICK_REFERENCE.md) - .gitignore reference

---

## Quick Reference

### Commands
```bash
git-pm install                    # Install with dependency resolution
git-pm install --no-resolve-deps  # Flat install (no dependencies)
git-pm install --no-gitignore     # Skip .gitignore management
git-pm update                     # Update branch-based packages
git-pm list                       # List installed packages
git-pm clean                      # Remove all packages
git-pm add <name> <repo> [opts]   # Add package to manifest
git-pm --version                  # Show version
```

### Files
```
git-pm.yaml          # Main manifest (commit)
git-pm.local.yaml    # Local overrides (DO NOT commit)
git-pm.lock          # Lockfile (optional - apps commit, libs ignore)
.git-pm.env          # Environment variables (DO NOT commit)
.git-packages/       # Installed packages (DO NOT commit)
.git-pm-cache/       # Cache directory (DO NOT commit)
```

### Environment Variables
```bash
AZURE_DEVOPS_PAT              # Azure DevOps token
GIT_PM_PACKAGES_DIR           # Packages directory (from .git-pm.env)
GIT_PM_PROJECT_ROOT           # Project root (from .git-pm.env)
GIT_PM_PACKAGE_<NAME>         # Individual package path (from .git-pm.env)
```

---

**Total Features:** 14 (8 core + 6 new in v0.2.0)  
**Lines of Code:** ~1200  
**Test Coverage:** Comprehensive CI/CD tests  
**Platforms:** Linux, macOS, Windows  
**Python:** 3.8+ required
