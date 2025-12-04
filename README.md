# git-pm: Git-based Package Manager

A lightweight package manager that uses git sparse-checkout to manage dependencies from monorepos and git repositories.

## Features

✅ **Hash-based caching** - Efficient content-addressable storage  
✅ **Sparse checkout** - Only downloads what you need  
✅ **Local development** - Easy overrides for local packages  
✅ **Cross-platform** - Works on Windows and Linux  
✅ **Multiple auth methods** - SSH, HTTPS, tokens for CI/CD  
✅ **Lockfile support** - Reproducible builds  
✅ **Zero dependencies** - Pure Python 3.7+, stdlib only  

## Files in This Implementation

```
.
├── git-pm.py                    # Main Python script
├── QUICKSTART.md                # Quick start guide
├── test-git-pm.sh              # Comprehensive test suite
├── simple-test.sh              # Simple manual test
└── examples/
    ├── git-pm.yaml             # Example manifest
    ├── git-pm.local.yaml       # Example local overrides
    ├── user-config.yaml        # Example user config
    ├── project-config.yaml     # Example project config
    └── .gitignore              # Recommended .gitignore entries
```

## Quick Start

### 1. Prerequisites

- Python 3.7 or higher
- Git command-line tool

### 2. Create a manifest

Create `git-pm.yaml`:

```yaml
packages:
  utils:
    repo: github.com/company/monorepo
    path: packages/utils
    ref:
      type: tag
      value: v1.2.0
```

### 3. Install packages

```bash
python git-pm.py install
```

That's it! Your packages are now in `.git-packages/`

## Running Tests

### Simple Test (Recommended First)

Run a simple end-to-end test:

```bash
./simple-test.sh
```

This will:
- Create a mock git repository
- Create a test project
- Install packages
- Verify everything works
- Test Python imports

### Comprehensive Test Suite

Run all tests:

```bash
./test-git-pm.sh all
```

Tests include:
1. Basic install
2. Local override
3. List command
4. Update command
5. Clean command
6. Config hierarchy
7. Multiple versions

Clean up test files:

```bash
./test-git-pm.sh clean
```

## Commands

```bash
# Install packages from manifest
python git-pm.py install

# Update packages (refresh branches)
python git-pm.py update

# List installed packages
python git-pm.py list

# Clean installed packages
python git-pm.py clean

# Clean packages and cache
python git-pm.py clean --cache

# Show version
python git-pm.py --version
```

## Configuration Hierarchy

Configuration is loaded and merged in this order:

1. **User config** (lowest priority)  
   `~/.git-pm/config.yaml`

2. **Project config** (overrides user)  
   `.git-pm/config.yaml`

3. **Environment variables** (highest priority)  
   `GIT_PM_TOKEN_*`, `GIT_PM_OVERRIDE_*`

## Directory Structure

```
your-project/
├── git-pm.yaml              # Main manifest (committed)
├── git-pm.local.yaml        # Local overrides (NOT committed)
├── git-pm.lock              # Lock file (committed for reproducibility)
├── .git-pm/
│   └── config.yaml          # Project config (team decides)
├── .git-packages/           # Installed packages (NOT committed)
│   ├── utils/               → symlink to cache
│   └── components/          → symlink to cache
└── .gitignore               # Ignore .git-packages, etc.

~/.cache/git-pm/             # User-level cache (Linux)
└── objects/
    ├── abc123/              # Cached package
    └── def456/              # Cached package

~/.git-pm/                   # User-level config
└── config.yaml
```

## Authentication

### SSH (Developers)

```bash
# Generate SSH key
ssh-keygen -t ed25519

# Add to GitHub/GitLab
cat ~/.ssh/id_ed25519.pub
```

### HTTPS with Token (CI/CD)

```bash
# Set environment variable
export GIT_PM_TOKEN_github_com="ghp_your_token"

# Run install
python git-pm.py install
```

### CI/CD Examples

**GitHub Actions:**

```yaml
- name: Install dependencies
  env:
    GIT_PM_TOKEN_github_com: ${{ secrets.GITHUB_TOKEN }}
  run: python git-pm.py install
```

**Azure DevOps:**

```yaml
- script: python git-pm.py install
  env:
    GIT_PM_TOKEN_dev_azure_com: $(System.AccessToken)
```

## Local Development

Working on a package locally? Create `git-pm.local.yaml`:

```yaml
overrides:
  utils:
    type: local
    path: ../my-local-utils
```

Run install:

```bash
python git-pm.py install
```

Now `.git-packages/utils` points to your local directory!

## Manifest Format

### Basic Package

```yaml
packages:
  package-name:
    repo: github.com/owner/repo      # Canonical identifier
    path: packages/subdir             # Path within repo
    ref:
      type: tag                       # tag, branch, or commit
      value: v1.0.0                   # Tag name, branch name, or commit SHA
```

### Tag Reference (Recommended for Production)

```yaml
packages:
  utils:
    repo: github.com/company/monorepo
    path: packages/utils
    ref:
      type: tag
      value: v1.2.0
```

### Branch Reference (Auto-updates)

```yaml
packages:
  utils:
    repo: github.com/company/monorepo
    path: packages/utils
    ref:
      type: branch
      value: main
```

### Commit Reference (Pinned)

```yaml
packages:
  utils:
    repo: github.com/company/monorepo
    path: packages/utils
    ref:
      type: commit
      value: abc123def456...
```

### Local Package

```yaml
packages:
  my-local-lib:
    type: local
    path: ../path/to/local/package
```

## Configuration Options

See `examples/user-config.yaml` and `examples/project-config.yaml` for all options.

Key options:

- `packages_dir` - Where to install packages (default: `.git-packages`)
- `cache_dir` - Where to cache repos (default: `~/.cache/git-pm`)
- `auto_update_branches` - Auto-update branches on install (default: `true`)
- `git_protocol` - SSH or HTTPS per domain
- `url_patterns` - Custom URL templates
- `credentials` - Token configuration

## Design Decisions

This implementation follows the specifications:

1. ✅ **Per-user cache** (Option 1) with future hybrid support
2. ✅ **Python script** for maximum compatibility
3. ✅ **Hash-based cache** structure
4. ✅ **Branch auto-update** on install
5. ✅ **Lockfile** for reproducibility
6. ✅ **Minimal prerequisites** (Python + Git)
7. ✅ **Python 3.7+** compatibility
8. ✅ **Cross-platform** (Windows & Linux)
9. ✅ **Config hierarchy** (user → project → env)
10. ✅ **Local overrides** for development

## Python Compatibility

The code is compatible with Python 3.7+ by avoiding:

- f-strings with `=` (3.8+)
- `|` dict merge operator (3.9+)
- `match/case` statements (3.10+)
- Modern typing features (3.10+)

Uses only Python standard library - no external dependencies required. Includes a built-in YAML parser.

## Windows Support

- Auto-detects symlink support
- Falls back to directory junctions if needed
- Uses platform-appropriate paths
- Handles both forward and backslashes

## Troubleshooting

### Git not found

The script will auto-detect and print installation instructions for your OS.

### Permission denied (symlinks on Windows)

Enable Developer Mode:
- Settings → Update & Security → For Developers → Developer Mode

Or run as Administrator.

### SSH authentication failed

Test SSH access:

```bash
ssh -T git@github.com
```

Set up SSH keys if needed.

### Package not found in repo

Verify the `path` matches the actual directory structure:

```bash
# Clone and check
git clone <repo-url>
cd repo
ls -la packages/  # Check structure
```

## GitHub Actions / CI/CD

The implementation includes ready-to-use GitHub Actions workflows:

### Release Automation
```bash
# Create a release - it's automatic!
git tag -a v0.0.1 -m "Release version 0.0.1"
git push origin v0.0.1

# Or use the helper script
./create-release.sh
```

When you push a version tag:
- ✅ Automatically creates tar.gz archive
- ✅ Generates release notes
- ✅ Creates GitHub Release
- ✅ Attaches archive as downloadable asset

### Continuous Integration
- Automatically tests on Python 3.7-3.12
- Runs on pull requests and pushes
- Validates code and documentation

See **[GITHUB_ACTIONS.md](computer:///mnt/user-data/outputs/git-pm-implementation/GITHUB_ACTIONS.md)** for complete documentation.

## Examples

All examples are in the `examples/` directory:

1. `git-pm.yaml` - Various package configurations
2. `git-pm.local.yaml` - Local development overrides
3. `user-config.yaml` - User-level preferences
4. `project-config.yaml` - Project-level settings
5. `.gitignore` - Recommended ignore patterns

## Contributing

This is a proof-of-concept implementation. For production use, consider:

- Adding progress bars for large downloads
- Parallel git operations
- Better error messages
- Dependency resolution
- Version constraint solving
- Package verification
- Signature checking

## License

MIT License - See project for details

## Version

v0.1.0 - Initial implementation

---

**For detailed usage, see [QUICKSTART.md](QUICKSTART.md)**
