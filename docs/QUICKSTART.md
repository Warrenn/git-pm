# git-pm Quick Start Guide

## Installation

### Quick Install from GitHub Release

```bash
# One-liner: Download latest release, extract, and cleanup
curl -L -o git-pm.tar.gz https://github.com/Warrenn/git-pm/releases/download/v0.0.6/git-pm-0.0.6.tar.gz && mkdir -p git-pm && tar -xzf git-pm.tar.gz -C git-pm --strip-components=1 && rm git-pm.tar.gz

# Verify installation
cd git-pm
python git-pm.py --version
```

Replace `v0.0.6` and `0.0.6` with the latest release version from: https://github.com/Warrenn/git-pm/releases

### Manual Download

Alternatively, download `git-pm.py` directly and run it with Python 3.8+.

### Prerequisites

- Python 3.8 or higher (3.7 may work but is not tested)
- Git command-line tool

**That's it!** No external dependencies needed - git-pm uses only Python's standard library.

## Basic Usage

### 1. Create a manifest file

**Option A: Use the add command (easier)**

```bash
python git-pm.py add utils github.com/company/monorepo \
    --path packages/utils \
    --ref-type tag \
    --ref-value v1.2.0
```

This creates `git-pm.json` automatically.

**See [ADD_COMMAND.md](ADD_COMMAND.md) for complete add command documentation.**

**Option B: Create manually**

Create `git-pm.json` in your project root:

```json
{
  "packages": {
    "utils": {
      "repo": "github.com/company/monorepo",
      "path": "packages/utils",
      "ref": {
        "type": "tag",
        "value": "v1.2.0"
      }
    }
  }
}
```

### 2. Install packages

```bash
python git-pm.py install
```

This will:
- Clone packages from git repositories
- Use sparse-checkout to get only the specified paths
- Cache packages in `~/.cache/git-pm/` (Linux) or `%LOCALAPPDATA%\git-pm\cache\` (Windows)
- Copy packages to `.git-packages/` directory
- Generate `git-pm.lock` for reproducibility

### 3. Use packages in your code

```python
# Your code can import from .git-packages/
import sys
sys.path.insert(0, '.git-packages')

from utils import helper
```

## Common Commands

```bash
# Add a package to manifest
python git-pm.py add utils github.com/company/utilities

# Add with specific version
python git-pm.py add auth github.com/company/monorepo \
    --path packages/auth \
    --ref-type tag \
    --ref-value v2.1.0

# Install all packages from manifest
python git-pm.py install

# Remove a package from manifest and disk
python git-pm.py remove utils

# Get or set configuration values
python git-pm.py config packages_dir
python git-pm.py config packages_dir ".deps"

# Clean installed packages
python git-pm.py clean
```

For complete add command documentation, see [ADD_COMMAND.md](ADD_COMMAND.md).

## Local Development

When working on a package locally:

1. Create `git-pm.local`:

```json
{
  "overrides": {
    "utils": {
      "type": "local",
      "path": "../my-local-utils"
    }
  }
}
```

2. Run install:

```bash
python git-pm.py install
```

Now `.git-packages/utils` points to your local directory!

## Authentication

### For SSH (recommended for developers)

Set up SSH keys with your git provider:

```bash
ssh-keygen -t ed25519
# Add public key to GitHub/GitLab/etc.
```

### For HTTPS with Token (recommended for CI/CD)

Set environment variables:

```bash
# GitHub
export GIT_PM_TOKEN_github_com="ghp_your_token_here"

# Azure DevOps
export GIT_PM_TOKEN_dev_azure_com="your_pat_here"
```

## CI/CD Example (GitHub Actions)

```yaml
jobs:
  build:
    steps:
      - uses: actions/checkout@v2
      
      - name: Install dependencies
        env:
          GIT_PM_TOKEN_github_com: ${{ secrets.GITHUB_TOKEN }}
        run: python git-pm.py install
      
      - name: Build
        run: python build.py
```

## Configuration

### User-level config: `~/.git-pm/config`

```json
{
  "git_protocol": {
    "github.com": "ssh"
  },
  "packages_dir": ".git-packages"
}
```

### Project-level config: `git-pm.config`

```json
{
  "packages_dir": ".custom-packages"
}
```

## .gitignore

Add to your `.gitignore`:

```
.git-packages/
git-pm.local
git-pm.lock
.git-pm.env
```

## Troubleshooting

### Git not found

Install git:
- **Ubuntu/Debian**: `sudo apt-get install git`
- **Windows**: Download from https://git-scm.com/download/win
- **macOS**: `brew install git`

### Permission denied (SSH)

Check SSH key setup:

```bash
ssh -T git@github.com
```

### Package not found in repo

Check that the `path` in your manifest matches the actual directory structure in the repository.

## Examples

See the `examples/` directory for complete examples of:
- `git-pm.json.example` - Main manifest
- `git-pm.local.example` - Local overrides
- `git-pm.config.example` - Configuration
- `.gitignore.example` - Recommended gitignore entries

## Additional Documentation

- [ADD_COMMAND.md](ADD_COMMAND.md) - Complete add command reference
- [REMOVE_COMMAND_QUICK_REFERENCE.md](REMOVE_COMMAND_QUICK_REFERENCE.md) - Remove command reference
- [CONFIG_QUICK_REFERENCE.md](CONFIG_QUICK_REFERENCE.md) - Config command reference
- [FEATURES.md](FEATURES.md) - Complete feature guide
- [REFERENCE.md](REFERENCE.md) - Quick reference card
