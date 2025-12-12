# git-pm v0.2.0 - Deployment Guide

## 📦 Release Package Contents

All files ready for GitHub release:

1. **git-pm.py** (34KB) - Main Python script
2. **install-git-pm.sh** (7KB) - Linux/macOS installer
3. **install-git-pm.ps1** (10KB) - Windows installer
4. **README.md** (14KB) - Complete documentation
5. **DEPENDENCY_RESOLUTION.md** (15KB) - Technical docs
6. **RELEASE_NOTES.md** (10KB) - Release information

**Total package size:** ~23KB (compressed)

## 🚀 GitHub Release Steps

### Step 1: Create Release on GitHub

1. Go to: https://github.com/Warrenn/git-pm/releases/new
2. Click "Create a new release"
3. Fill in:
   - **Tag:** `v0.2.0`
   - **Title:** `git-pm v0.2.0 - Global Installation with Dependency Resolution`
   - **Description:** (use content from RELEASE_NOTES.md)

### Step 2: Upload Files

Upload these files as release assets:

```
✅ git-pm.py                   (required for installers)
✅ install-git-pm.sh           (optional, but helpful)
✅ install-git-pm.ps1          (optional, but helpful)
✅ README.md                   (optional)
✅ DEPENDENCY_RESOLUTION.md    (optional)
```

**Critical:** The `git-pm.py` file MUST be uploaded with exact filename.

### Step 3: Commit Installer Scripts to Repo

The installer scripts should be in the repo root for the one-liner install to work:

```bash
git add install-git-pm.sh install-git-pm.ps1 git-pm.py README.md DEPENDENCY_RESOLUTION.md
git commit -m "Release v0.2.0: Global installation with full dependency resolution"
git tag v0.2.0
git push origin main
git push origin v0.2.0
```

### Step 4: Test Installation

**Linux/macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/Warrenn/git-pm/main/install-git-pm.sh | bash
```

**Windows:**
```powershell
irm https://raw.githubusercontent.com/Warrenn/git-pm/main/install-git-pm.ps1 | iex
```

Should download from: `https://github.com/Warrenn/git-pm/releases/latest/download/git-pm.py`

## 📋 Pre-Release Checklist

Before creating the GitHub release:

- [ ] All files created and ready
- [ ] Scripts have execute permissions (Linux/macOS)
- [ ] Tested `git-pm --version` output
- [ ] Verified Python script has shebang: `#!/usr/bin/env python3`
- [ ] README has correct repo URLs
- [ ] Installer scripts point to correct repo
- [ ] Tag is v0.2.0
- [ ] No sensitive data in files

## 🧪 Testing After Release

### Test 1: Direct Download
```bash
curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/git-pm.py -o git-pm.py
chmod +x git-pm.py
./git-pm.py --version
# Expected: git-pm 0.2.0

# Or call with Python
python3 git-pm.py --version
# Expected: git-pm 0.2.0
```

### Test 2: Installer (Linux/macOS)
```bash
curl -fsSL https://raw.githubusercontent.com/Warrenn/git-pm/main/install-git-pm.sh | bash
git-pm --version
# Expected: git-pm 0.2.0
```

### Test 3: Installer (Windows)
```powershell
irm https://raw.githubusercontent.com/Warrenn/git-pm/main/install-git-pm.ps1 | iex
git-pm --version
# Expected: git-pm 0.2.0
```

### Test 4: End-to-End
```bash
# Create test project
mkdir test-project && cd test-project

# Add package
git-pm add test github.com/Warrenn/git-pm --ref-type tag --ref-value v0.2.0

# Verify manifest
cat git-pm.yaml

# Install (will fail if no dependencies, but that's OK for test)
git-pm install --no-resolve-deps

# Clean up
cd .. && rm -rf test-project
```

## 📝 Release Description Template

Copy this to GitHub release description:

```markdown
# git-pm v0.2.0 - Global Installation with Full Dependency Resolution

## 🎉 Major Release

This release transforms git-pm into a globally-installed package manager with automatic dependency resolution.

## ✨ New Features

### Global Installation
- **Linux/macOS:** Installs to `~/.local/bin/git-pm`
- **Windows:** Installs to `%USERPROFILE%\.git-pm\git-pm.bat`
- Automatic PATH configuration
- Works from any directory
- Survives system restarts

### Full Dependency Resolution
- Automatic recursive dependency discovery
- Reads `git-pm.yaml` from each package
- Topological sorting (dependencies first)
- Complete dependency tree in lockfile
- Opt-out with `--no-resolve-deps` flag

### Branch Auto-Resolution
- Branches automatically resolve to latest commit SHA
- All references to same branch use same commit
- `git-pm update` pulls latest commits for branches
- Deterministic installs via lockfile

### Enhanced Local Development
- Local overrides now use **symlinks** instead of copying
- Live updates during development
- Faster iteration cycle

### Azure DevOps Integration
- Built-in PAT token injection via `AZURE_DEVOPS_PAT` env var
- Works seamlessly in Azure Pipelines
- No code changes needed for different auth methods

## 🚀 Quick Start

### One-Line Installation

**Linux/macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/Warrenn/git-pm/main/install-git-pm.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/Warrenn/git-pm/main/install-git-pm.ps1 | iex
```

### Basic Usage

```bash
# Add packages
git-pm add utils github.com/company/monorepo --path packages/utils --ref-type tag --ref-value v1.0.0

# Install with dependency resolution
git-pm install

# Update branch-based packages
git-pm update

# List installed
git-pm list
```

## 📋 Requirements

- Python 3.7+
- git
- Internet connection (for initial install)

## 🔄 Migration from v0.1.x

### Breaking Changes
1. **Global installation required** - Script no longer in project directory
2. **Dependency resolution on by default** - Use `--no-resolve-deps` to disable
3. **Local overrides use symlinks** - Faster, live updates

### Migration Steps
```bash
# 1. Install globally
curl -fsSL https://raw.githubusercontent.com/Warrenn/git-pm/main/install-git-pm.sh | bash

# 2. Remove old script from project (optional)
rm git-pm.py

# 3. Works from anywhere now!
cd your-project
git-pm install
```

## 📚 Documentation

- **README.md** - Complete usage guide
- **DEPENDENCY_RESOLUTION.md** - Technical deep-dive
- **RELEASE_NOTES.md** - Detailed release information

## 🐛 Known Issues

- PATH update may require terminal restart
- Windows installer requires PowerShell 5.0+

## 🙏 Feedback

Please report issues at: https://github.com/Warrenn/git-pm/issues

## 📥 Assets

- **git-pm.py** - Main Python script (required by installers)
- **install-git-pm.sh** - Linux/macOS installer
- **install-git-pm.ps1** - Windows installer
- **README.md** - Complete documentation
- **DEPENDENCY_RESOLUTION.md** - Technical documentation

**Commands after installation:**
- `git-pm install` (via wrapper)
- `git-pm.py install` (direct)
- `python git-pm.py install` (explicit)
```

## 🎯 Post-Release Tasks

After creating the release:

1. **Update README.md** in repo root (if different)
2. **Announce** release (if applicable)
3. **Test** installers from various environments
4. **Monitor** GitHub issues for bug reports
5. **Update** documentation based on feedback

## 🔧 Troubleshooting Release Issues

### Issue: Installer can't download git-pm

**Check:**
1. Release is published (not draft)
2. File named exactly `git-pm` (no extension)
3. URL is correct: `https://github.com/Warrenn/git-pm/releases/latest/download/git-pm`

**Fix:**
```bash
# Test URL manually
curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/git-pm -o test-git-pm
# Should download successfully
```

### Issue: Raw installer script not found

**Check:**
1. Scripts committed to main branch
2. Files named correctly: `install-git-pm.sh` and `install-git-pm.ps1`
3. In repo root (not subdirectory)

**Fix:**
```bash
git ls-remote --heads origin main
# Verify main branch exists and scripts are there
```

### Issue: Permission denied (Linux/macOS)

**Check:**
1. Installer sets executable bit: `chmod +x`
2. File has shebang: `#!/usr/bin/env python3`

**Fix:**
```bash
# Manual fix
chmod +x ~/.local/bin/git-pm
```

## 📊 File Checksums

For verification:

```bash
# Generate checksums
cd /mnt/user-data/outputs
sha256sum git-pm install-git-pm.sh install-git-pm.ps1 README.md DEPENDENCY_RESOLUTION.md > checksums.txt
```

Include checksums in release notes for security-conscious users.

## 🎓 Next Steps

1. Create GitHub release with tag v0.2.0
2. Upload `git-pm` as release asset
3. Commit installer scripts to repo
4. Test one-liner installations
5. Share with team
6. Monitor for issues

---

**Ready for deployment!** All files are in `/mnt/user-data/outputs/`
