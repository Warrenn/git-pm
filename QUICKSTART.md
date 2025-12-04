# git-pm Quick Start Guide

## Installation

No installation required! Just download `git-pm.py` and run it with Python 3.7+.

### Prerequisites

- Python 3.7 or higher
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

This creates `git-pm.yaml` automatically.

**See [ADD_COMMAND.md](ADD_COMMAND.md) for complete add command documentation.**

**Option B: Create manually**

Create `git-pm.yaml` in your project root:

```yaml
packages:
  utils:
    repo: github.com/company/monorepo
    path: packages/utils
    ref:
      type: tag
      value: v1.2.0
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

# Update packages (refresh branches to latest)
python git-pm.py update

# List installed packages
python git-pm.py list

# Clean installed packages
python git-pm.py clean

# Clean packages and cache
python git-pm.py clean --cache
```

For complete add command documentation, see [ADD_COMMAND.md](ADD_COMMAND.md).

## Local Development

When working on a package locally:

1. Create `git-pm.local.yaml`:

```yaml
overrides:
  utils:
    type: local
    path: ../my-local-utils
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

### User-level config: `~/.git-pm/config.yaml`

```yaml
git_protocol:
  github.com: ssh
packages_dir: .git-packages
```

### Project-level config: `.git-pm/config.yaml`

```yaml
packages_dir: .custom-packages
auto_update_branches: false
```

## .gitignore

Add to your `.gitignore`:

```
.git-packages/
git-pm.local.yaml
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
- `git-pm.yaml` - Main manifest
- `git-pm.local.yaml` - Local overrides
- `user-config.yaml` - User configuration
- `project-config.yaml` - Project configuration
- `.gitignore` - Recommended gitignore entries
