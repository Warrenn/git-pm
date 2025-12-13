# git-pm Quick Reference Card

**💡 For detailed add command documentation, see [ADD_COMMAND.md](ADD_COMMAND.md)**

## Installation
```bash
# No installation needed - just run the script!
python git-pm.py --version
```

## Basic Commands
```bash
# Add package to manifest
python git-pm.py add <n> <repo> [--path PATH] [--ref-type TYPE] [--ref-value VALUE]

# Examples
python git-pm.py add utils github.com/company/utils
python git-pm.py add auth github.com/company/monorepo --path packages/auth --ref-type tag --ref-value v2.0.0

# Package operations
python git-pm.py install      # Install all packages
python git-pm.py update       # Update branch references
python git-pm.py list         # List installed packages
python git-pm.py clean        # Remove installed packages
python git-pm.py clean --cache # Also remove cache
```

See [ADD_COMMAND.md](ADD_COMMAND.md) for complete add command documentation.

## Manifest Format (git-pm.yaml)
```yaml
packages:
  package-name:
    repo: github.com/owner/repo    # Canonical identifier
    path: packages/subdir           # Path within repo
    ref:
      type: tag                     # tag, branch, or commit
      value: v1.0.0                 # Tag/branch name or commit SHA
```

## Local Override (git-pm.local.yaml)
```yaml
overrides:
  package-name:
    type: local
    path: ../local-dev/package-name
```

## Config Locations
```
~/.git-pm/config.yaml           # User-level config
.git-pm/config.yaml             # Project-level config  
git-pm.local.yaml               # Local overrides
```

## Environment Variables
```bash
# Authentication tokens
export GIT_PM_TOKEN_github_com="ghp_..."
export GIT_PM_TOKEN_dev_azure_com="pat_..."

# Use in CI/CD
GIT_PM_TOKEN_github_com=${{ secrets.GITHUB_TOKEN }} python git-pm.py install
```

## Common Config Options
```yaml
packages_dir: .git-packages           # Where to install
cache_dir: ~/.cache/git-pm            # Where to cache
auto_update_branches: true            # Update branches on install

git_protocol:
  github.com: ssh                     # ssh or https

url_patterns:
  github.com: "git@github.com:{path}.git"

credentials:
  dev.azure.com:
    token: ${ADO_PAT}                 # From environment
```

## .gitignore Entries
```gitignore
.git-packages/
git-pm.local.yaml
```

## Package Usage in Code
```python
import sys
sys.path.insert(0, '.git-packages')

from mypackage import something
```

## Reference Types

### Tag (Immutable, Recommended for Production)
```yaml
ref:
  type: tag
  value: v1.0.0
```

### Branch (Mutable, Auto-updates)
```yaml
ref:
  type: branch
  value: main
```

### Commit (Immutable, Absolute Pin)
```yaml
ref:
  type: commit
  value: abc123def456...
```

### Local (Development)
```yaml
type: local
path: ../local-path
```

## Testing
```bash
./simple-test.sh              # Quick test
./test-git-pm.sh all          # Full test suite
./test-git-pm.sh clean        # Clean up tests
```

## Typical Workflow

### Setup (Using add command - Recommended)
```bash
# Add packages using add command
python git-pm.py add utils github.com/company/monorepo \
    --path packages/utils \
    --ref-type tag \
    --ref-value v1.0.0

# Install
python git-pm.py install
```

See [ADD_COMMAND.md](ADD_COMMAND.md) for more examples.

### Setup (Manual YAML)
```bash
# 1. Create manifest
cat > git-pm.yaml << EOF
packages:
  utils:
    repo: github.com/company/monorepo
    path: packages/utils
    ref:
      type: tag
      value: v1.0.0
EOF

# 2. Install
python git-pm.py install
```

### Development
```bash
# 1. Clone package locally
git clone git@github.com:company/monorepo.git ../monorepo-local

# 2. Override to use local version
cat > git-pm.local.yaml << EOF
overrides:
  utils:
    type: local
    path: ../monorepo-local/packages/utils
EOF

# 3. Reinstall
python git-pm.py install

# 4. Make changes in ../monorepo-local/packages/utils
# Changes are immediately available!

# 5. When done, remove override
rm git-pm.local.yaml
python git-pm.py install
```

### CI/CD (GitHub Actions)
```yaml
- name: Install dependencies
  env:
    GIT_PM_TOKEN_github_com: ${{ secrets.GITHUB_TOKEN }}
  run: python git-pm.py install
```

## Directory Structure
```
your-project/
├── git-pm.yaml               # Manifest (commit)
├── git-pm.lock               # Lock file (commit)
├── .git-packages/            # Packages (DON'T commit)
│   ├── utils/                → /cache/abc123/packages/utils
│   └── components/           → /cache/def456/packages/components
└── src/
    └── main.py               # Your code

~/.cache/git-pm/objects/      # Cache (shared across projects)
├── abc123/                   # Cached package
└── def456/                   # Cached package
```

## Troubleshooting

### Git not found
```bash
# Ubuntu/Debian
sudo apt-get install git

# macOS
brew install git

# Windows
# Download from git-scm.com
```

### Permission denied (Windows symlinks)
```
Enable Developer Mode:
Settings → Update & Security → For Developers → Developer Mode
```

### SSH authentication failed
```bash
# Test SSH
ssh -T git@github.com

# Generate key if needed
ssh-keygen -t ed25519
```

### Package not found in repo
```
Verify path exists in repository:
git clone <repo-url>
cd repo
ls -la <path>
```

## Pro Tips

1. **Use tags for production** - Immutable, reliable
2. **Use branches for development** - Auto-updates
3. **Commit lockfile** - Ensures reproducibility
4. **Don't commit .git-packages/** - It's generated
5. **Use local overrides** - Don't modify manifest for dev work
6. **Set up user config** - Default preferences for all projects
7. **Use environment variables in CI/CD** - Never commit tokens

## Get Help
```bash
python git-pm.py --help
python git-pm.py install --help
```

## Documentation
- `README.md` - Full documentation
- `QUICKSTART.md` - Step-by-step guide
- `ADD_COMMAND.md` - Add command reference
- `DOCUMENTATION.md` - Design details
- `examples/` - Working examples
