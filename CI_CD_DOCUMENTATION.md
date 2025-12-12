# CI/CD Documentation

## 📋 Overview

The git-pm project uses GitHub Actions for comprehensive testing and automated releases.

## 🧪 CI Workflow (`.github/workflows/ci.yml`)

Runs on every push and pull request to ensure code quality and functionality.

### Test Jobs

#### 1. `test-dependency-resolution`
Tests the core dependency resolution functionality.

**Tests:**
- ✅ **Nested dependency discovery** - Verifies recursive package discovery
  - Creates 3-level dependency tree: `api` → `utils` → `base`
  - Verifies all dependencies are auto-discovered
  - Checks correct topological sort order
  
- ✅ **Circular dependency detection** - Ensures cycles are caught
  - Creates `pkg-a` → `pkg-b` → `pkg-a` circular dependency
  - Verifies error is raised with clear message
  
- ✅ **Branch resolution** - Tests branch → commit conversion
  - References branch in manifest
  - Verifies lockfile contains resolved commit SHA
  - Checks original branch reference is preserved
  
- ✅ **Flat install** - Tests `--no-resolve-deps` flag
  - Installs only root packages
  - Verifies dependencies are NOT installed

**Mock Repository:**
Creates a real git repository with package structure:
```
packages/
├── base/
│   ├── git-pm.yaml (no dependencies)
│   └── base.py
├── utils/
│   ├── git-pm.yaml (depends on base)
│   └── utils.py
└── api/
    ├── git-pm.yaml (depends on utils and base)
    └── api.py
```

#### 2. `test-global-installation`
Tests global installation on Linux and macOS.

**Tests:**
- ✅ **Installer execution** - Runs `install-git-pm.sh`
- ✅ **File placement** - Verifies files in `~/.local/bin/`
- ✅ **Wrapper creation** - Checks `git-pm` wrapper exists
- ✅ **Permissions** - Ensures executable bit is set
- ✅ **Command invocation** - Tests all 3 methods:
  - `git-pm --version` (wrapper)
  - `git-pm.py --version` (direct)
  - `python3 git-pm.py --version` (explicit)
- ✅ **Real project test** - Installs actual packages
- ✅ **All commands** - Tests install, list, clean

**Platforms:**
- Ubuntu (latest)
- macOS (latest)

#### 3. `test-windows-installation`
Tests installation and functionality on Windows.

**Tests:**
- ✅ **Installation simulation** - Creates directory structure
- ✅ **Batch wrapper** - Creates `git-pm.bat`
- ✅ **Command invocation** - Tests both methods:
  - `git-pm --version` (batch)
  - `python git-pm.py --version` (direct)
- ✅ **Real project test** - Full workflow on Windows

#### 4. `test-python-versions`
Tests compatibility across Python versions.

**Versions Tested:**
- Python 3.8
- Python 3.9
- Python 3.10
- Python 3.11
- Python 3.12

**Note:** Python 3.7 is no longer tested due to EOL and Ubuntu 24.04 compatibility.

**Tests:**
- ✅ Version command works
- ✅ Basic install/clean cycle
- ✅ Lockfile generation

#### 5. `lint-and-syntax`
Validates code quality.

**Checks:**
- ✅ Python syntax (`py_compile`)
- ✅ Shebang line correct
- ✅ Bash script syntax

### Triggers

```yaml
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  workflow_dispatch:
```

- Runs on push to main/develop
- Runs on all pull requests
- Can be manually triggered

## 🚀 Release Workflow (`.github/workflows/release.yml`)

Automates the release process with comprehensive release notes.

### Jobs

#### 1. `create-release`
Creates GitHub release with auto-generated notes.

**Steps:**

1. **Version Extraction**
   - Gets version from tag or workflow input
   - Removes 'v' prefix for number comparison
   
2. **Version Verification**
   - Checks `__version__` in `git-pm.py` matches tag
   - Fails if mismatch detected
   
3. **Changelog Generation**
   - Gets previous tag
   - Generates commit list since last release
   - Formats as markdown list
   
4. **Statistics Collection**
   - Counts commits since last release
   - Tracks files changed
   - Counts lines added/removed
   
5. **Release Notes Generation**
   - Uses template with placeholders
   - Includes changelog
   - Adds installation commands
   - Links to documentation
   
6. **GitHub Release Creation**
   - Creates release with generated notes
   - Uploads assets: `git-pm.py`, installers, docs
   - Publishes (not draft)

**Placeholders Used:**
- `${{ github.repository }}` - Full repo name (owner/repo)
- `${{ github.repository_owner }}` - Repository owner
- `${{ github.event.repository.name }}` - Repository name
- `${{ github.server_url }}` - GitHub server URL
- `${{ github.ref_name }}` - Tag/branch name
- `${{ github.sha }}` - Commit SHA
- `${{ github.actor }}` - User who triggered

#### 2. `test-installation`
Verifies release assets are downloadable.

**Tests:**
- ✅ Direct download from release URL
- ✅ File verification
- ✅ Version check
- ✅ Runs on Linux, macOS, Windows

### Triggers

```yaml
on:
  push:
    tags:
      - 'v*.*.*'
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to release'
        required: true
```

- Automatically on version tags (`v1.0.0`, `v0.2.0`, etc.)
- Manual trigger with version input

### Example Usage

**Automatic Release:**
```bash
git tag v0.2.1
git push origin v0.2.1
# Workflow automatically runs
```

**Manual Release:**
1. Go to Actions → Release → Run workflow
2. Enter version: `v0.2.1`
3. Click "Run workflow"

## 📝 Release Notes Template

The release workflow generates comprehensive notes including:

### Sections

1. **Release Information**
   - Version number
   - Release date
   - Repository links
   - Tag link

2. **Statistics**
   - Number of commits
   - Files changed
   - Lines added/removed

3. **What's New**
   - Feature highlights
   - Major changes
   - Improvements

4. **Quick Start**
   - Installation commands (with repo URLs)
   - Basic usage examples

5. **Requirements**
   - Python version
   - Dependencies

6. **Changelog**
   - Auto-generated commit list
   - Links to commits

7. **Migration Guide**
   - Breaking changes
   - Migration steps

8. **Assets**
   - Download URLs (with repo placeholders)
   - Command examples

9. **Documentation**
   - Links to README (with repo URLs)
   - Links to technical docs

10. **Examples**
    - Terraform modules
    - Shared libraries
    - Bitbucket support

### Placeholder Examples

```markdown
**Repository:** [${{ env.REPO_FULL }}](${{ env.REPO_URL }})
```
Becomes:
```markdown
**Repository:** [Warrenn/git-pm](https://github.com/Warrenn/git-pm)
```

```bash
curl -fsSL ${{ env.REPO_URL }}/raw/${{ github.ref_name }}/install-git-pm.sh | bash
```
Becomes:
```bash
curl -fsSL https://github.com/Warrenn/git-pm/raw/v0.2.0/install-git-pm.sh | bash
```

## 🔧 Environment Variables

Both workflows use these environment variables:

```yaml
env:
  REPO_OWNER: ${{ github.repository_owner }}
  REPO_NAME: ${{ github.event.repository.name }}
  REPO_FULL: ${{ github.repository }}
  REPO_URL: ${{ github.server_url }}/${{ github.repository }}
```

**Available everywhere in workflow:**
- `${{ env.REPO_OWNER }}` - e.g., "Warrenn"
- `${{ env.REPO_NAME }}` - e.g., "git-pm"
- `${{ env.REPO_FULL }}` - e.g., "Warrenn/git-pm"
- `${{ env.REPO_URL }}` - e.g., "https://github.com/Warrenn/git-pm"

## 📊 Test Coverage

### What's Tested

✅ **Dependency Resolution**
- Nested dependencies (3+ levels)
- Circular dependency detection
- Branch to commit resolution
- Flat install option
- Topological sorting

✅ **Installation**
- Linux installer
- macOS installer
- Windows installer
- File placement
- PATH configuration
- Command availability

✅ **Commands**
- `install` with and without resolution
- `list` - show installed packages
- `clean` - remove packages
- `--version` - show version
- `--help` - show help

✅ **Python Compatibility**
- Python 3.8, 3.9, 3.10, 3.11, 3.12
- Cross-platform (Linux, macOS, Windows)
- Note: Python 3.7 EOL, not tested

✅ **Code Quality**
- Python syntax validation
- Bash syntax validation
- Shebang verification

### What's NOT Tested (Future)

⏳ Authentication methods (SSH, tokens)
⏳ Azure DevOps integration
⏳ Bitbucket integration
⏳ Local overrides (symlinks)
⏳ Update command
⏳ Add command

## 🐛 Troubleshooting CI

### Tests Failing Locally But Pass in CI

**Cause:** Different git versions, Python versions, or OS

**Solution:**
```bash
# Use act to run CI locally
brew install act  # macOS
apt install act   # Linux

# Run specific job
act -j test-dependency-resolution

# Run entire workflow
act -W .github/workflows/ci.yml
```

### Release Workflow Not Triggering

**Cause:** Tag not pushed or wrong format

**Solution:**
```bash
# Ensure tag is annotated
git tag -a v0.2.1 -m "Release v0.2.1"

# Push tag
git push origin v0.2.1

# Verify tag exists on remote
git ls-remote --tags origin
```

### Version Mismatch Error

**Cause:** `__version__` in `git-pm.py` doesn't match tag

**Solution:**
```bash
# Update version in git-pm.py
sed -i 's/__version__ = ".*"/__version__ = "0.2.1"/' git-pm.py

# Commit
git add git-pm.py
git commit -m "Bump version to 0.2.1"

# Tag
git tag v0.2.1
git push origin main v0.2.1
```

### Release Assets Missing

**Cause:** Files not committed to repo

**Solution:**
```bash
# Ensure all files committed
git add git-pm.py install-git-pm.sh install-git-pm.ps1 README.md DEPENDENCY_RESOLUTION.md
git commit -m "Add release files"
git push

# Re-tag
git tag -d v0.2.1  # Delete locally
git push origin :refs/tags/v0.2.1  # Delete remotely
git tag v0.2.1
git push origin v0.2.1
```

## 📚 Best Practices

### Before Releasing

1. ✅ Update version in `git-pm.py`
2. ✅ Update documentation if needed
3. ✅ Test locally:
   ```bash
   python3 git-pm.py --version
   python3 git-pm.py install --no-resolve-deps
   ```
4. ✅ Commit all changes
5. ✅ Create annotated tag:
   ```bash
   git tag -a v0.2.1 -m "Release v0.2.1: <brief description>"
   ```
6. ✅ Push tag:
   ```bash
   git push origin main v0.2.1
   ```

### After Release

1. ✅ Verify release page looks correct
2. ✅ Test installation commands from release notes
3. ✅ Check asset downloads work
4. ✅ Test on at least one platform

### Semantic Versioning

Follow semver: `MAJOR.MINOR.PATCH`

- **MAJOR** - Breaking changes (e.g., 1.0.0 → 2.0.0)
- **MINOR** - New features, backwards compatible (e.g., 0.2.0 → 0.3.0)
- **PATCH** - Bug fixes (e.g., 0.2.0 → 0.2.1)

## 🎯 Future Improvements

### Potential Additions

1. **Code Coverage**
   - Add pytest with coverage reports
   - Upload to Codecov

2. **Performance Tests**
   - Benchmark installation times
   - Track cache performance

3. **Security Scanning**
   - Dependabot alerts
   - CodeQL analysis

4. **Documentation Tests**
   - Verify all links work
   - Test code examples in docs

5. **Integration Tests**
   - Real GitHub/GitLab/Bitbucket repos
   - Azure DevOps pipelines
   - Various authentication methods

6. **Release Automation**
   - Auto-bump version
   - Generate changelog from conventional commits
   - Create release branch

## 📖 References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Actions Context](https://docs.github.com/en/actions/learn-github-actions/contexts)
- [GitHub Actions Environment Variables](https://docs.github.com/en/actions/learn-github-actions/environment-variables)
- [Semantic Versioning](https://semver.org/)

## 🎓 Summary

**CI Workflow:**
- Tests on every push/PR
- Validates Python 3.7-3.12 compatibility
- Tests installers on Linux, macOS, Windows
- Comprehensive dependency resolution tests
- Syntax and lint checks

**Release Workflow:**
- Triggered by version tags
- Auto-generates release notes with placeholders
- Creates GitHub release with assets
- Tests installation from release URL
- Fully automated with manual fallback

**Key Benefits:**
- ✅ Catches bugs before merge
- ✅ Ensures cross-platform compatibility
- ✅ Automated releases save time
- ✅ Consistent release notes
- ✅ Repository-agnostic (uses placeholders)

---

**All workflows are ready to use!** Just push and tag to trigger.
