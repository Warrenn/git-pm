# Automatic .gitignore Management

## 🎯 The Problem

git-pm creates several files that should NEVER be committed to version control:

| File | Why Not Commit |
|------|----------------|
| `.git-packages/` | Installed dependencies (like node_modules) |
| `.git-pm.env` | Absolute paths unique to each developer |
| `git-pm.local` | Local overrides specific to your machine |
| `git-pm.lock` | Optional - some teams commit, others don't |

**Problem:** Developers might accidentally commit these files, causing:
- ❌ Merge conflicts on `.git-pm.env` (different absolute paths)
- ❌ Binary files in repo (installed packages)
- ❌ Local overrides affecting other developers
- ❌ Repository bloat

## ✅ Solution: Automatic .gitignore Management

git-pm now **automatically** manages `.gitignore` entries on every `git-pm install`.

### What It Does

1. Checks if `.gitignore` exists
2. Checks if git-pm entries are present
3. Adds missing entries automatically
4. **Never duplicates** existing entries
5. Preserves all your existing .gitignore content

## 📝 Added Entries

When you run `git-pm install`, these entries are automatically added if missing:

```gitignore
# git-pm - Package manager files
.git-packages/
.git-pm.env
git-pm.local.yaml
git-pm.lock
```

## 🚀 Usage

### Default Behavior (Automatic)

```bash
git-pm install
```

**Output:**
```
🚀 git-pm install (dependency resolution)
📝 Updating .gitignore...
  ✓ Added: .git-packages/
  ✓ Added: .git-pm.env
  ✓ Added: git-pm.local.yaml
  ✓ Added: git-pm.lock
✓ Git detected: git version 2.52.0
📋 Loading configuration...
...
```

### Skip .gitignore Management (Optional)

If you want to manage `.gitignore` manually:

```bash
git-pm install --no-gitignore
```

**Output:**
```
🚀 git-pm install (dependency resolution)
✓ Git detected: git version 2.52.0
📋 Loading configuration...
...
```

## 🔍 Behavior Details

### Scenario 1: No .gitignore File

```bash
# Before
project/
├── git-pm.yaml
└── main.tf

# Run
$ git-pm install

# After
project/
├── .gitignore          ← Created
├── git-pm.yaml
├── .git-packages/
└── main.tf
```

**Created .gitignore:**
```gitignore
# git-pm - Package manager files
.git-packages/
.git-pm.env
git-pm.local.yaml
git-pm.lock
```

### Scenario 2: Existing .gitignore (No git-pm Entries)

**Before:**
```gitignore
# Terraform
*.tfstate
*.tfstate.backup
.terraform/
```

**After `git-pm install`:**
```gitignore
# Terraform
*.tfstate
*.tfstate.backup
.terraform/

# git-pm - Package manager files
.git-packages/
.git-pm.env
git-pm.local.yaml
git-pm.lock
```

### Scenario 3: .gitignore Already Has Some Entries

**Before:**
```gitignore
# Terraform
.terraform/

# git-pm
.git-packages/
```

**After `git-pm install`:**
```
✓ .gitignore up to date
```

**Only adds missing entries:**
```gitignore
# Terraform
.terraform/

# git-pm
.git-packages/
.git-pm.env       ← Added
git-pm.local.yaml ← Added
git-pm.lock       ← Added
```

### Scenario 4: All Entries Already Present

**Before:**
```gitignore
.git-packages/
.git-pm.env
git-pm.local.yaml
git-pm.lock
```

**After `git-pm install`:**
```
✓ .gitignore up to date
```

No changes made, no duplicate entries added.

## 🎓 Smart Detection

### Trailing Slash Handling

git-pm recognizes these as equivalent:
- `.git-packages`
- `.git-packages/`

So if you already have `.git-packages` in .gitignore, it won't add `.git-packages/`.

### Comment Detection

If any line in .gitignore mentions "git-pm", the comment header is not re-added:

**Your .gitignore:**
```gitignore
# My custom git-pm section
.git-packages/
```

**git-pm won't add:**
```gitignore
# git-pm - Package manager files  ← Won't duplicate
```

### Pattern Matching

git-pm checks for:
- Exact matches
- Trailing slash variants
- Already ignored patterns

**Example:**
```gitignore
# Your existing entry
**/.git-packages/  ← Covers .git-packages/
```

git-pm detects this covers `.git-packages/` and won't add it again.

## ⚙️ Why Each Entry Is Needed

### .git-packages/

**Contains:** Installed package source code  
**Why ignore:** Like `node_modules/`, these are dependencies that should be installed fresh  
**Size:** Can be 100+ MB  
**Commit impact:** ❌ Bloats repository, causes merge conflicts

### .git-pm.env

**Contains:** Absolute paths unique to each developer  
**Example:**
```bash
# Developer A
export GIT_PM_PACKAGES_DIR="/Users/alice/projects/myapp/.git-packages"

# Developer B  
export GIT_PM_PACKAGES_DIR="C:\Users\bob\dev\myapp\.git-packages"
```
**Why ignore:** ❌ Paths differ per machine, causes conflicts  
**Regenerated:** On every `git-pm install`

### git-pm.local.yaml

**Contains:** Local development overrides  
**Example:**
```yaml
overrides:
  my-package:
    type: local
    path: ../my-package  # Local development path
```
**Why ignore:** ❌ Specific to your machine, not relevant to others  
**Personal:** Each developer has different local paths

### git-pm.lock

**Contains:** Resolved dependency versions  
**Should you commit?** 
- ✅ **Yes** for applications (reproducible builds)
- ❌ **No** for libraries (let consumers resolve)

**Default:** git-pm adds to .gitignore (you can remove if you want to commit it)

## 🛠️ Manual Management

### Remove Automatic Management

If you prefer manual control:

**Option 1:** Use the flag every time
```bash
git-pm install --no-gitignore
```

**Option 2:** Create a wrapper script
```bash
# install.sh
#!/bin/bash
git-pm install --no-gitignore "$@"
```

**Option 3:** Edit .gitignore yourself
git-pm only adds missing entries, so if all entries are present, it does nothing.

### Remove git-pm.lock from .gitignore

If you want to commit the lockfile:

```bash
# Edit .gitignore
# Remove or comment out this line:
# git-pm.lock

# Commit the lockfile
git add git-pm.lock
git commit -m "Add dependency lockfile"
```

git-pm won't re-add it if you remove it.

### Custom .gitignore Structure

git-pm works with any .gitignore structure:

**Your custom organization:**
```gitignore
# ====================
# Build Outputs
# ====================
*.tfstate
.terraform/

# ====================
# Dependencies
# ====================
node_modules/
.git-packages/    ← git-pm respects your organization

# ====================
# Environment Files
# ====================
.env
.git-pm.env       ← Adds entries in your structure
```

## 🔍 Debugging

### Check What Will Be Added

```bash
# Before install
cat .gitignore

# Run install
git-pm install

# Check what was added
git diff .gitignore
```

### Verify Entries

```bash
# Check if entries exist
grep -E '(\.git-packages|\.git-pm\.env|git-pm\.local\.yaml|git-pm\.lock)' .gitignore

# Should output all four patterns
```

### Test Ignore Rules

```bash
# Create test files
touch .git-pm.env
mkdir .git-packages

# Check if git ignores them
git status --porcelain

# Should NOT show these files
# If they appear, .gitignore isn't working
```

## 🚨 Common Issues

### Issue 1: Entries Not Added

**Symptom:**
```bash
git-pm install
# No .gitignore message
```

**Causes:**
1. Entries already exist
2. Used `--no-gitignore` flag
3. Not in a git repository

**Solution:**
```bash
# Verify you're in a git repo
git status

# Check existing .gitignore
cat .gitignore

# Force re-add (remove entries first)
# Then run: git-pm install
```

### Issue 2: Files Still Tracked

**Symptom:**
```bash
$ git status
modified: .git-pm.env
```

**Cause:** Files were committed BEFORE adding to .gitignore

**Solution:**
```bash
# Remove from git tracking (keeps local file)
git rm --cached .git-pm.env
git rm --cached -r .git-packages/
git rm --cached git-pm.local.yaml

# Commit the removal
git commit -m "Remove git-pm files from tracking"

# Now .gitignore will work
git status  # Should be clean
```

### Issue 3: Duplicate Entries

**Symptom:**
```gitignore
.git-packages/
.git-packages/
```

**Cause:** Bug or manual addition while git-pm also added it

**Solution:**
```bash
# Manually edit .gitignore
# Remove duplicates
# git-pm won't re-add them
```

### Issue 4: Wrong Pattern Syntax

**Symptom:** Files not being ignored

**Cause:** Custom patterns that don't work

**Solution:**
```bash
# Test .gitignore patterns
git check-ignore -v .git-pm.env

# Should output:
# .gitignore:3:.git-pm.env    .git-pm.env

# If nothing, pattern is wrong
```

## 📊 Best Practices

### For Applications

```gitignore
# Commit lockfile for reproducible builds
# .git-packages/       ← Keep this
# .git-pm.env          ← Keep this
# git-pm.local.yaml    ← Keep this
# git-pm.lock          ← REMOVE THIS (commit lockfile)
```

### For Libraries

```gitignore
# Don't commit lockfile
.git-packages/       ← Keep
.git-pm.env          ← Keep
git-pm.local.yaml    ← Keep
git-pm.lock          ← Keep (don't commit)
```

### For Team Projects

**Add to README:**
```markdown
## Setup

1. Clone repository
2. Run `git-pm install`
3. git-pm automatically updates .gitignore

Note: .git-pm.env is NOT committed (contains absolute paths)
```

### For CI/CD

**.gitignore is committed**, so CI environment will respect it:
```yaml
# .github/workflows/ci.yml
steps:
  - uses: actions/checkout@v3
  - run: git-pm install
    # .gitignore is already set up ✅
  - run: terraform plan
```

## ✅ Verification Checklist

After `git-pm install`, verify:

- [ ] `.gitignore` exists
- [ ] Contains `.git-packages/`
- [ ] Contains `.git-pm.env`
- [ ] Contains `git-pm.local.yaml`
- [ ] Contains `git-pm.lock` (or removed if you want to commit it)
- [ ] `git status` doesn't show these files
- [ ] No duplicate entries in .gitignore

**Quick check:**
```bash
git status --short
# Should NOT show:
# .git-packages/
# .git-pm.env
# git-pm.local.yaml
```

## 📝 Summary

**Feature:** Automatic .gitignore management  
**Trigger:** Every `git-pm install` (unless `--no-gitignore`)  
**Behavior:** Adds missing entries, never duplicates  
**Files:** .git-packages/, .git-pm.env, git-pm.local.yaml, git-pm.lock  
**Override:** Use `--no-gitignore` flag  
**Safe:** Never modifies existing entries or structure  

**Bottom line:** Just run `git-pm install` and forget about it - .gitignore is handled automatically! 🎉

---

**Files Modified:**
- `git-pm.py` - Added `update_gitignore()` method and `--no-gitignore` flag

**Commit message:**
```
Feature: Automatic .gitignore management

Automatically add git-pm files to .gitignore on install:
- .git-packages/
- .git-pm.env
- git-pm.local.yaml
- git-pm.lock

Features:
- Smart detection (no duplicates)
- Preserves existing .gitignore structure
- Creates .gitignore if missing
- Handles trailing slash variants
- Skip with --no-gitignore flag

Prevents accidentally committing:
- Installed packages (bloat)
- Local absolute paths (conflicts)
- Machine-specific overrides

Fixes: Accidental commits of environment-specific files
```
