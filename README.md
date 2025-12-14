# git-pm - Git Package Manager

A lightweight, dependency-resolving package manager that uses git sparse-checkout to manage packages from monorepos and regular repositories. Includes full dependency resolution with explicit versioning.

## Features

### Core Features

✅ **Full Dependency Resolution** - Automatically discovers and installs all dependencies  
✅ **Explicit Versioning** - No version ranges, uses exact tags/branches/commits  
✅ **Branch Resolution** - Branches resolve to latest commit automatically  
✅ **Independent Versioning** - Each package can be at different commits  
✅ **Local Development** - Symlink local packages for live development with automatic override detection  
✅ **Zero Runtime Dependencies** - Pure Python 3.8+ with built-in YAML parser  
✅ **Cross-Platform** - Works on Linux, macOS, and Windows  
✅ **Azure DevOps Support** - Built-in PAT token injection for CI/CD  
✅ **Git Sparse-Checkout** - Efficient cloning of monorepo subdirectories  
✅ **Smart Caching** - Fast repeated installs with intelligent cache management  
✅ **Nested Dependency Symlinks** - Automatically creates symlinks inside packages for their dependencies  
✅ **Environment Variables** - Auto-generates `.git-pm.env` with package paths for scripts  
✅ **Windows Symlink Support** - Intelligent fallback to junction points on Windows (no admin required)  
✅ **Automatic .gitignore** - Manages .gitignore entries to prevent accidental commits  
✅ **Path Resolution** - Solves dependency path conflicts between development and consumption  
✅ **Local Override Discovery** - Checks local overrides before cloning from remote  
✅ **Package Management** - Add, remove, and configure packages with simple commands  

## Quick Start

### One-Line Installation

**Linux/macOS:**
```bash
curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/install-git-pm.sh | bash
```

**Windows (PowerShell as Administrator recommended):**
```powershell
irm https://github.com/Warrenn/git-pm/releases/latest/download/install-git-pm.ps1 | iex
```

**Windows (User-level, no admin):**
```powershell
irm https://github.com/Warrenn/git-pm/releases/latest/download/install-git-pm.ps1 | iex
```

**Windows (System-level, requires admin):**
```powershell
irm https://github.com/Warrenn/git-pm/releases/latest/download/install-git-pm.ps1 | iex -System
```

### Basic Usage

```bash
# Create a manifest
git-pm add utils github.com/company/monorepo --path packages/utils --ref-type tag --ref-value v1.0.0

# Install packages (with dependency resolution)
git-pm install

# Remove a package
git-pm remove utils

# Configure settings
git-pm config packages_dir

# Clean up
git-pm clean
```

**See also:**
- [Add Command Documentation](docs/ADD_COMMAND.md)
- [Remove Command Reference](docs/REMOVE_COMMAND_QUICK_REFERENCE.md)
- [Config Command Reference](docs/CONFIG_QUICK_REFERENCE.md)

## Installation

### Requirements

- **Python 3.8+** - Required (3.7 may work but is not tested)
- **git** - Required
- **curl or wget** - For installation (Linux/macOS)

### Global Installation

The installer automatically:
1. ✅ Checks for Python 3.8+ and git
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
# git-pm 0.4.0
```

## Usage

### Creating a Manifest

Create `git-pm.json` in your project root:

```json
{
  "packages": {
    "utils": {
      "repo": "github.com/company/monorepo",
      "path": "packages/utils",
      "ref": {
        "type": "tag",
        "value": "v1.0.0"
      }
    },
    "logger": {
      "repo": "github.com/company/monorepo",
      "path": "packages/logger",
      "ref": {
        "type": "branch",
        "value": "main"
      }
    },
    "legacy-lib": {
      "repo": "github.com/other/repo",
      "path": "lib",
      "ref": {
        "type": "commit",
        "value": "abc123def456"
      }
    }
  }
}
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
git-pm install
```

Features:
- Automatically discovers nested dependencies
- Resolves branches to latest commits
- Installs in correct order (dependencies first)
- Manages .gitignore entries automatically (use `--no-gitignore` to skip)

### Removing Packages

```bash
git-pm remove <package-name>
```

Removes a package from the manifest and disk, including unused dependencies.

### Configuration

```bash
git-pm config <key> [value]
```

Get or set configuration values like `packages_dir` or `cache_dir`.

### Cleaning Up

```bash
git-pm clean
```

Removes:
- All installed packages (`.git-packages/`)

## Dependency Resolution

### How It Works

1. **Discovery**: Recursively finds all dependencies by reading `git-pm.json` from each package
2. **Branch Resolution**: Branches resolve to latest commit SHA
3. **Explicit Versions**: All dependencies use exact tags/commits/resolved-commits
4. **Topological Sort**: Installs in correct order (dependencies before dependents)
5. **Caching**: Smart caching with branch re-fetching

### Example

**Your project (`git-pm.json`):**
```json
{
  "packages": {
    "api-client": {
      "repo": "github.com/company/monorepo",
      "path": "packages/api",
      "ref": {
        "type": "tag",
        "value": "v3.0.0"
      }
    }
  }
}
```

**api-client's dependencies (`packages/api/git-pm.json`):**
```json
{
  "packages": {
    "logger": {
      "repo": "github.com/company/monorepo",
      "path": "packages/logger",
      "ref": {
        "type": "branch",
        "value": "main"
      }
    },
    "http-utils": {
      "repo": "github.com/company/monorepo",
      "path": "packages/http",
      "ref": {
        "type": "tag",
        "value": "v1.5.0"
      }
    }
  }
}
```

**http-utils' dependencies (`packages/http/git-pm.json`):**
```json
{
  "packages": {
    "logger": {
      "repo": "github.com/company/monorepo",
      "path": "packages/logger",
      "ref": {
        "type": "branch",
        "value": "main"
      }
    }
  }
}
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
✅ Installation complete! (3/3 packages)
```

### Branch Behavior

**Key principle:** All references to the same branch use the same (latest) commit.

When a branch is referenced:
1. Resolve branch to latest commit SHA
2. All packages referencing that branch use the same resolved commit

**Example:**
```json
{
  "packages": {
    "pkg-a": {
      "ref": {
        "type": "branch",
        "value": "main"
      }
    },
    "pkg-b": {
      "ref": {
        "type": "branch",
        "value": "main"
      }
    }
  }
}
```

Both install with commit `abc12345` (same resolved commit for `main`).

## Local Development

### Local Overrides

Create `git-pm.local` for local development:

```json
{
  "overrides": {
    "utils": {
      "type": "local",
      "path": "../local-dev/utils"
    }
  }
}
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
cat > git-pm.local << EOF
{
  "overrides": {
    "utils": {
      "type": "local",
      "path": "../utils-dev"
    }
  }
}
EOF

# 3. Reinstall with override
git-pm install

# 4. Edit ../utils-dev/utils.py
# Changes immediately visible in .git-packages/utils (symlinked)

# 5. Remove override and reinstall from git
rm git-pm.local
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

### User Configuration (`git-pm.config`)

Optional configuration file in project root:

```json
{
  "packages_dir": ".deps",
  "cache_dir": "/custom/cache/path",
  "git_protocol": {
    "github.com": "ssh",
    "gitlab.com": "https"
  },
  "url_patterns": {
    "custom.git.com": "https://custom.git.com/{path}.git"
  },
  "azure_devops_pat": "your-token"
}
```

### Cache Location

**Default cache locations:**
- **Linux/macOS:** `~/.cache/git-pm/`
- **Windows:** `%LOCALAPPDATA%\git-pm\cache\`

Override with `cache_dir` in config or `GIT_PM_CACHE_DIR` environment variable.

## Examples

### Terraform Modules

```json
{
  "packages": {
    "azure-bootstrap": {
      "repo": "dev.azure.com/org/terraform",
      "path": "modules/bootstrap",
      "ref": {
        "type": "tag",
        "value": "v1.0.0"
      }
    },
    "azure-networking": {
      "repo": "dev.azure.com/org/terraform",
      "path": "modules/networking",
      "ref": {
        "type": "tag",
        "value": "v2.1.0"
      }
    }
  }
}
```

```hcl
# main.tf
module "bootstrap" {
  source = "./.git-packages/azure-bootstrap"
  # ...
}
```

### Shared Libraries

```json
{
  "packages": {
    "common-utils": {
      "repo": "github.com/company/shared-libs",
      "path": "utils",
      "ref": {
        "type": "branch",
        "value": "main"
      }
    },
    "validators": {
      "repo": "github.com/company/shared-libs",
      "path": "validators",
      "ref": {
        "type": "tag",
        "value": "v3.0.0"
      }
    }
  }
}
```

```python
# app.py
import sys
sys.path.insert(0, '.git-packages')

from common_utils import helpers
from validators import email
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

Install Python 3.8+:
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

```json
{
  "packages": {
    "utils-v1": {
      "repo": "github.com/company/monorepo",
      "path": "packages/utils",
      "ref": {
        "type": "tag",
        "value": "v1.0.0"
      }
    },
    "utils-v2": {
      "repo": "github.com/company/monorepo",
      "path": "packages/utils",
      "ref": {
        "type": "tag",
        "value": "v2.0.0"
      }
    }
  }
}
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

## New Features Guide

### Nested Dependency Symlinks

When PackageB depends on PackageA, git-pm automatically creates symlinks inside PackageB:

```
.git-packages/
├── packageA/
└── packageB/
    ├── main.tf
    └── .git-packages/           ← Auto-created!
        └── packageA -> ../../packageA
```

**Your code (works in both development and consumption):**
```hcl
# packageB/main.tf
module "package_a" {
  source = ".git-packages/packageA"  # Works everywhere!
}
```

**Installation output:**
```bash
$ git-pm install
...
🔗 Creating dependency symlinks...
  ✓ packageB/packageA -> packageA
```

**Benefits:**
- ✅ Same path works in development and consumption
- ✅ No manual symlink management
- ✅ Works with Terraform and other tools
- ✅ Automatic on every install

### Environment Variables

git-pm generates `.git-pm.env` with absolute paths for use in scripts:

**Generated `.git-pm.env`:**
```bash
export GIT_PM_PACKAGES_DIR="/absolute/path/to/.git-packages"
export GIT_PM_PROJECT_ROOT="/absolute/path/to/project"
export GIT_PM_PACKAGE_PACKAGEA="/absolute/path/to/.git-packages/packageA"
export GIT_PM_PACKAGE_PACKAGEB="/absolute/path/to/.git-packages/packageB"
```

**Usage in scripts:**
```bash
#!/bin/bash
source .git-pm.env

# Use absolute paths
terraform -chdir="$GIT_PM_PACKAGE_PACKAGEB" init
terraform -chdir="$GIT_PM_PACKAGE_PACKAGEB" apply
```

**Python example:**
```python
import os
packages_dir = os.environ['GIT_PM_PACKAGES_DIR']
```

**Makefile example:**
```makefile
include .git-pm.env

deploy:
	cd $(GIT_PM_PACKAGE_PACKAGEB) && terraform apply
```

### Windows Symlink Support

git-pm automatically handles Windows symlinks with intelligent fallback:

**Scenario 1: Developer Mode Enabled**
```bash
🔗 Creating dependency symlinks...
  ✓ packageB/packageA -> packageA  (symbolic link)
```

**Scenario 2: No Developer Mode (Auto-Fallback)**
```bash
🔗 Creating dependency symlinks...
  ⚠️  Windows: Symlinks require Developer Mode
     Falling back to junction points...
  ✓ packageB/packageA -> packageA  (junction)
```

**Enable Developer Mode (optional but recommended):**
1. Settings → Update & Security → For developers
2. Toggle "Developer Mode" ON
3. Restart terminal
4. Run `git-pm install`

**Both methods work identically with Terraform!**

### Automatic .gitignore Management

git-pm automatically manages `.gitignore` entries on every install:

**Auto-added entries:**
```gitignore
# git-pm - Package manager files
.git-packages/
.git-pm.env
git-pm.local
git-pm.lock
```

**Installation output:**
```bash
$ git-pm install
📝 Updating .gitignore...
  ✓ Added: .git-packages/
  ✓ Added: .git-pm.env
  ✓ Added: git-pm.local
  ✓ Added: git-pm.lock
```

**Skip automatic management:**
```bash
git-pm install --no-gitignore
```

**Why these files should be ignored:**
- `.git-packages/` - Installed dependencies (like node_modules)
- `.git-pm.env` - Absolute paths (unique per developer)
- `git-pm.local` - Local overrides (machine-specific)
- `git-pm.lock` - Optional (commit for apps, ignore for libraries)

### Local Development with Overrides

Create `git-pm.local` to override packages with local paths during development:

**git-pm.json:**
```json
{
  "packages": {
    "my-package": {
      "repo": "github.com/company/repo",
      "path": "packages/my-package",
      "ref": {
        "type": "tag",
        "value": "v1.0.0"
      }
    }
  }
}
```

**git-pm.local:**
```json
{
  "overrides": {
    "my-package": {
      "type": "local",
      "path": "../local-dev/my-package"
    }
  }
}
```

**Installation:**
```bash
$ git-pm install
🔍 Discovering dependencies...
📦 Discovering my-package...
  Using local override: ../local-dev/my-package  ← No remote clone!
📦 Installing my-package...
  Override: my-package -> local (symlinked)
```

**Benefits:**
- ✅ No remote clones during development
- ✅ Live updates (symlinks)
- ✅ Fast iteration
- ✅ Works offline
- ✅ Automatic detection (checks before cloning)

## Contributing

Issues and PRs welcome at https://github.com/Warrenn/git-pm

## License

MIT License - See LICENSE file

## Credits

Created by Warrenn Enslin (https://github.com/Warrenn)
