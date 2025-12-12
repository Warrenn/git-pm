# .gitignore Management - Quick Reference

## 🎯 What It Does

git-pm **automatically** adds these to `.gitignore` on every install:

```gitignore
# git-pm - Package manager files
.git-packages/        ← Installed packages (like node_modules)
.git-pm.env           ← Absolute paths (unique per developer)
git-pm.local.yaml     ← Local overrides (your machine only)
git-pm.lock           ← Dependency versions (optional)
```

## 🚀 Usage

### Default (Automatic)

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
...
```

### Skip (Manual Control)

```bash
git-pm install --no-gitignore
```

## ✅ Smart Behavior

- ✅ **Creates** .gitignore if missing
- ✅ **Preserves** all existing content
- ✅ **Never duplicates** entries
- ✅ **Detects** trailing slash variants (`.git-packages` vs `.git-packages/`)
- ✅ **Only adds** missing entries

## 📋 Why Each File Should Be Ignored

| File | Why Ignore | Size | Impact |
|------|------------|------|--------|
| `.git-packages/` | Installed dependencies | 100+ MB | ❌ Bloat + conflicts |
| `.git-pm.env` | Absolute paths | 1 KB | ❌ Per-machine conflicts |
| `git-pm.local.yaml` | Local overrides | <1 KB | ❌ Machine-specific |
| `git-pm.lock` | Dependency versions | 5 KB | ✅/❌ Optional |

## 🔧 Examples

### First Install (No .gitignore)

```bash
$ ls -la
-rw-r--r-- git-pm.yaml

$ git-pm install
📝 Updating .gitignore...
  ✓ Created .gitignore
  ✓ Added: .git-packages/
  ✓ Added: .git-pm.env
  ✓ Added: git-pm.local.yaml
  ✓ Added: git-pm.lock

$ cat .gitignore
# git-pm - Package manager files
.git-packages/
.git-pm.env
git-pm.local.yaml
git-pm.lock
```

### Existing .gitignore (Some Entries)

**Before:**
```gitignore
.terraform/
.git-packages/
```

**After install:**
```
✓ .gitignore up to date

# Only adds missing:
.terraform/
.git-packages/
.git-pm.env          ← Added
git-pm.local.yaml    ← Added
git-pm.lock          ← Added
```

### All Entries Present

```bash
$ git-pm install
✓ .gitignore up to date

# No changes made
```

## 🎓 Common Scenarios

### Want to Commit Lockfile?

```bash
# Edit .gitignore - remove this line:
# git-pm.lock

# Commit it
git add git-pm.lock
git commit -m "Add dependency lockfile"

# git-pm won't re-add it
```

### Files Already Tracked?

If you committed files BEFORE adding to .gitignore:

```bash
# Remove from git (keeps local files)
git rm --cached .git-pm.env
git rm --cached -r .git-packages/

git commit -m "Remove git-pm files from tracking"
```

### Prefer Manual Control?

```bash
# Always use flag
git-pm install --no-gitignore

# Or manage .gitignore yourself
# git-pm only adds missing entries
```

## ✅ Verification

```bash
# Check status
git status

# Should NOT show:
# .git-packages/
# .git-pm.env
# git-pm.local.yaml

# Verify entries
grep git-pm .gitignore
```

## 📝 Summary

**Default:** Automatic (just run `git-pm install`)  
**Override:** `--no-gitignore` flag  
**Safe:** Never duplicates or breaks existing .gitignore  
**Smart:** Only adds what's missing  

**Just works!** No manual .gitignore management needed. 🎉

---

**Commands:**
```bash
git-pm install              # Automatic .gitignore management
git-pm install --no-gitignore  # Skip .gitignore updates
```

**Files managed:**
- `.git-packages/` - Dependencies
- `.git-pm.env` - Environment variables
- `git-pm.local.yaml` - Local overrides  
- `git-pm.lock` - Dependency lockfile
