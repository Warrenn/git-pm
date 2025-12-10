# git-pm - Git Package Manager

A lightweight, dependency-resolving package manager that uses git sparse-checkout to manage packages from monorepos and regular repositories.

**Version 0.2.0** - Full dependency resolution with explicit versioning

## Features

✅ **Full Dependency Resolution** - Automatically discovers and installs all dependencies  
✅ **Explicit Versioning** - No version ranges, uses exact tags/branches/commits  
✅ **Branch Resolution** - Branches resolve to latest commit automatically  
✅ **Independent Versioning** - Each package can be at different commits  
✅ **Local Development** - Symlink local packages for live development  
✅ **Zero Runtime Dependencies** - Pure Python 3.7+ with built-in YAML parser  
✅ **Cross-Platform** - Works on Linux, macOS, and Windows  
✅ **Azure DevOps Support** - Built-in PAT token injection for CI/CD  
✅ **Git Sparse-Checkout** - Efficient cloning of monorepo subdirectories  
✅ **Smart Caching** - Fast repeated installs with intelligent cache management  

## Quick Start

### One-Line Installation

**Linux/macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/Warrenn/git-pm/main/install-git-pm.sh | bash
```

**Windows (PowerShell as Administrator recommended):**
```powershell
irm https://raw.githubusercontent.com/Warrenn/git-pm/main/install-git-pm.ps1 | iex
```

**Windows (User-level, no admin):**
```powershell
irm https://raw.githubusercontent.com/Warrenn/git-pm/main/install-git-pm.ps1 | iex
```

**Windows (System-level, requires admin):**
```powershell
irm https://raw.githubusercontent.com/Warrenn/git-pm/main/install-git-pm.ps1 | iex -System
```

### Basic Usage

```bash
# Create a manifest
git-pm add utils github.com/company/monorepo --path packages/utils --ref-type tag --ref-value v1.0.0

# Install packages (with dependency resolution)
git-pm install

# List installed packages
git-pm list

# Update branch-based packages
git-pm update

# Clean up
git-pm clean
```

## Installation

### Requirements

- **Python 3.7+** - Required
- **git** - Required
- **curl or wget** - For installation (Linux/macOS)

### Global Installation

The installer automatically:
1. ✅ Checks for Python 3.7+ and git
2. ✅ Downloads the latest release (`git-pm.py`)
3. ✅ Installs to user directory
4. ✅ Adds to PATH
5. ✅ Creates command wrapper for convenience
6. ✅ Verifies installation

**Installation Locations:**

- **Linux/macOS:** 
  - Script: `~/.local/bin/git-pm.py`
  - Wrapper: `~/.local/bin/git-pm` (calls git-pm.py)
- **Windows:** 
  - Script: `%USERPROFILE%\.git-pm\git-pm.py`
  - Wrapper: `%USERPROFILE%\.git-pm\git-pm.bat`

After installation, use either:
- `git-pm install` (via wrapper)
- `git-pm.py install` (direct Python script)
- `python git-pm.py install` (explicit Python call)

### Verification

```bash
git-pm --version
# git-pm 0.2.0
```

## Usage

### Creating a Manifest

Create `git-pm.yaml` in your project root:

```yaml
packages:
  utils:
    repo: github.com/company/monorepo
    path: packages/utils
    ref:
      type: tag
      value: v1.0.0
  
  logger:
    repo: github.com/company/monorepo
    path: packages/logger
    ref:
      type: branch
      value: main
  
  legacy-lib:
    repo: github.com/other/repo
    path: lib
    ref:
      type: commit
      value: abc123def456
```

### Adding Packages

```bash
# Add with explicit tag
git-pm add mylib github.com/user/repo --path packages/mylib --ref-type tag --ref-value v2.1.0

# Add with branch (resolves to latest commit)
git-pm add utils github.com/user/monorepo --path packages/utils --ref-type branch --ref-value main

# Add with commit SHA
git-pm add legacy github.com/user/repo --ref-type commit --ref-value abc123def

# Add from repository root (no path)
git-pm add standalone github.com/user/standalone-repo --ref-type tag --ref-value v1.0.0
```

### Installing Packages

```bash
# Install with dependency resolution (default)
git-pm install

# Install without dependency resolution (flat install)
git-pm install --no-resolve-deps
```

**With dependency resolution:**
- Automatically discovers nested dependencies
- Resolves branches to latest commits
- Installs in correct order (dependencies first)
- Creates detailed lockfile with full dependency tree

**Without dependency resolution:**
- Only installs packages from root manifest
- Faster for simple projects
- No recursive discovery

### Updating Packages

```bash
git-pm update
```

Updates **branch-based** packages to latest commits. Tag and commit references are immutable and won't update.

### Listing Packages

```bash
git-pm list
```

Shows:
- Installed packages with versions
- Dependencies (with `--resolve-deps`)
- Installation order
- Local overrides (symlinked)

### Cleaning Up

```bash
git-pm clean
```

Removes:
- All installed packages (`.git-packages/`)
- Lockfile (`git-pm.lock`)

## Dependency Resolution

### How It Works

1. **Discovery**: Recursively finds all dependencies by reading `git-pm.yaml` from each package
2. **Branch Resolution**: Branches resolve to latest commit SHA
3. **Explicit Versions**: All dependencies use exact tags/commits/resolved-commits
4. **Topological Sort**: Installs in correct order (dependencies before dependents)
5. **Caching**: Smart caching with branch re-fetching

### Example

**Your project (`git-pm.yaml`):**
```yaml
packages:
  api-client:
    repo: github.com/company/monorepo
    path: packages/api
    ref:
      type: tag
      value: v3.0.0
```

**api-client's dependencies (`packages/api/git-pm.yaml`):**
```yaml
packages:
  logger:
    repo: github.com/company/monorepo
    path: packages/logger
    ref:
      type: branch
      value: main
  
  http-utils:
    repo: github.com/company/monorepo
    path: packages/http
    ref:
      type: tag
      value: v1.5.0
```

**http-utils' dependencies (`packages/http/git-pm.yaml`):**
```yaml
packages:
  logger:
    repo: github.com/company/monorepo
    path: packages/logger
    ref:
      type: branch
      value: main
```

**Installation:**
```bash
$ git-pm install

🚀 git-pm install (dependency resolution)
✓ Git detected: git version 2.40.0
📋 Loading configuration...
📄 Loading manifest...
🔍 Discovering dependencies...
📦 Discovering api-client...
  Found 2 dependencies
  📦 Discovering logger (depth 1)...
    Resolving branch 'main' to commit...
      ✓ Branch 'main' -> abc12345
  📦 Discovering http-utils (depth 1)...
    Found 1 dependencies
    📦 Discovering logger (depth 2)...
      (already discovered)
   Found 3 total packages
📦 Planning installation order...
   Order: logger -> http-utils -> api-client
📥 Installing 3 package(s)...
📦 Installing logger...
    ✓ Copied: packages/logger -> .git-packages/logger
📦 Installing http-utils...
    ✓ Copied: packages/http -> .git-packages/http
📦 Installing api-client...
    ✓ Copied: packages/api -> .git-packages/api
💾 Saving lockfile...
✅ Installation complete! (3/3 packages)
```

### Branch Behavior

**Key principle:** All references to the same branch use the same (latest) commit.

When a branch is referenced:
1. Resolve branch to latest commit SHA
2. All packages referencing that branch use the same resolved commit
3. On `git-pm update`, re-resolve branches to new latest commits
4. Cached in lockfile for deterministic reinstalls

**Example:**
```yaml
# Both packages reference main branch
packages:
  pkg-a:
    ref:
      type: branch
      value: main
  pkg-b:
    ref:
      type: branch
      value: main
```

Both install with commit `abc12345` (same resolved commit for `main`).

## Local Development

### Local Overrides

Create `git-pm.local.yaml` for local development:

```yaml
overrides:
  utils:
    type: local
    path: ../local-dev/utils  # Relative or absolute path
```

**Behavior:**
- Creates **symlink** instead of copying
- Changes in local directory immediately visible
- Perfect for development workflow
- Overrides only apply to specified packages

### Example Workflow

```bash
# 1. Install packages normally
git-pm install

# 2. Create local override for development
cat > git-pm.local.yaml << EOF
overrides:
  utils:
    type: local
    path: ../utils-dev
EOF

# 3. Reinstall with override
git-pm install

# 4. Edit ../utils-dev/utils.py
# Changes immediately visible in .git-packages/utils (symlinked)

# 5. Remove override and reinstall from git
rm git-pm.local.yaml
git-pm install
```

## Azure DevOps Integration

### CI/CD with PAT Token

**In Azure DevOps Pipeline:**

```yaml
steps:
  - bash: |
      export AZURE_DEVOPS_PAT=$(System.AccessToken)
      git-pm install
    displayName: 'Install dependencies'
```

**Environment Variable:**
```bash
export AZURE_DEVOPS_PAT="your-token"
git-pm install
```

git-pm automatically injects the PAT into Azure DevOps repository URLs for authentication.

### Manual Authentication

For other git providers:

```bash
# GitHub
export GIT_PM_TOKEN_github_com="ghp_yourtoken"

# GitLab
export GIT_PM_TOKEN_gitlab_com="glpat-yourtoken"

# Generic
export GIT_PM_TOKEN_git_example_com="your-token"

git-pm install
```

## Configuration

### User Configuration (`git-pm.config.yaml`)

Optional configuration file in project root:

```yaml
# Custom packages directory
packages_dir: .deps

# Custom cache directory
cache_dir: /custom/cache/path

# Git protocol preference by domain
git_protocol:
  github.com: ssh
  gitlab.com: https

# Custom URL patterns
url_patterns:
  custom.git.com: "https://custom.git.com/{path}.git"

# Azure DevOps PAT (alternatively use environment variable)
azure_devops_pat: "your-token"
```

### Cache Location

**Default cache locations:**
- **Linux/macOS:** `~/.cache/git-pm/`
- **Windows:** `%LOCALAPPDATA%\git-pm\cache\`

Override with `cache_dir` in config or `GIT_PM_CACHE_DIR` environment variable.

## Examples

### Terraform Modules

```yaml
packages:
  azure-bootstrap:
    repo: dev.azure.com/org/terraform
    path: modules/bootstrap
    ref:
      type: tag
      value: v1.0.0
  
  azure-networking:
    repo: dev.azure.com/org/terraform
    path: modules/networking
    ref:
      type: tag
      value: v2.1.0
```

```hcl
# main.tf
module "bootstrap" {
  source = "./.git-packages/azure-bootstrap"
  # ...
}
```

### Shared Libraries

```yaml
packages:
  common-utils:
    repo: github.com/company/shared-libs
    path: utils
    ref:
      type: branch
      value: main
  
  validators:
    repo: github.com/company/shared-libs
    path: validators
    ref:
      type: tag
      value: v3.0.0
```

```python
# app.py
import sys
sys.path.insert(0, '.git-packages')

from common_utils import helpers
from validators import email
```

## Lockfile Format

`git-pm.lock` (JSON):

```json
{
  "packages": {
    "logger": {
      "repo": "github.com/company/monorepo",
      "path": "packages/logger",
      "ref": {
        "type": "commit",
        "value": "abc12345"
      },
      "original_ref": {
        "type": "branch",
        "value": "main"
      },
      "commit": "abc12345",
      "dependencies": [],
      "installed_at": "2024-01-15T10:30:00"
    },
    "utils": {
      "repo": "github.com/company/monorepo",
      "path": "packages/utils",
      "ref": {
        "type": "tag",
        "value": "v2.0.0"
      },
      "commit": "def67890",
      "dependencies": ["logger"],
      "installed_at": "2024-01-15T10:30:01"
    }
  },
  "installation_order": ["logger", "utils"]
}
```

## Troubleshooting

### Command Not Found

**Linux/macOS:**
```bash
# Check if installed
ls -la ~/.local/bin/git-pm

# Add to PATH manually
export PATH="$HOME/.local/bin:$PATH"

# Make permanent (bash)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

**Windows:**
```powershell
# Check if installed
dir $env:USERPROFILE\.git-pm

# Add to PATH manually
$env:Path += ";$env:USERPROFILE\.git-pm"

# Or run directly
& "$env:USERPROFILE\.git-pm\git-pm.bat" --version
```

### Python Not Found

Install Python 3.7+:
- **Ubuntu/Debian:** `sudo apt install python3`
- **macOS:** `brew install python3`
- **Windows:** https://www.python.org/downloads/

### Git Not Found

Install git:
- **Ubuntu/Debian:** `sudo apt install git`
- **macOS:** `brew install git` or use Xcode Command Line Tools
- **Windows:** https://git-scm.com/download/win

### Authentication Issues

For private repositories:

1. **Use SSH keys:**
   ```bash
   git config --global url."git@github.com:".insteadOf "https://github.com/"
   ```

2. **Use tokens:**
   ```bash
   export GIT_PM_TOKEN_github_com="your-token"
   ```

3. **Azure DevOps:**
   ```bash
   export AZURE_DEVOPS_PAT="your-token"
   ```

## Advanced Usage

### Monorepo with Multiple Versions

```yaml
packages:
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

Both versions install side-by-side as `utils-v1` and `utils-v2`.

### Git Submodules Alternative

Replace git submodules with git-pm:

**Before (submodules):**
```bash
git submodule add https://github.com/company/lib lib
git submodule update --init --recursive
```

**After (git-pm):**
```bash
git-pm add lib github.com/company/lib --ref-type tag --ref-value v1.0.0
git-pm install
```

**Benefits:**
- No `.gitmodules` file to manage
- Version pinning with tags
- Dependency resolution
- Faster (sparse checkout)

## Contributing

Issues and PRs welcome at https://github.com/Warrenn/git-pm

## License

MIT License - See LICENSE file

## Credits

Created by Warrenn Enslin (https://github.com/Warrenn)
