# git-pm config - Quick Reference

## Commands

```bash
# Get value
git-pm config packages_dir

# Set (project)
git-pm config packages_dir ".deps"

# Set (user)
git-pm config --global cache_dir "/tmp/cache"

# Unset (project)
git-pm config --unset packages_dir

# Unset (user)
git-pm config --unset --global cache_dir

# List all
git-pm config --list
```

---

## Valid Keys

- `packages_dir` - Where packages install (default: `.git-packages`)
- `cache_dir` - Cache location (default: `~/.cache/git-pm`)
- `git_protocol` - Git protocol settings (dict)
- `url_patterns` - URL mappings (dict)
- `azure_devops_pat` - Azure PAT token (string)

---

## Config Files

| Level | File | Flag | Priority |
|-------|------|------|----------|
| Project | `git-pm.config` | (default) | Highest |
| User | `~/.git-pm/config` | `--global` | Medium |
| Default | Built-in | N/A | Lowest |

---

## Precedence Example

```bash
# Default: packages_dir = .git-packages

$ git-pm config --global packages_dir ".vendor"
# Now: .vendor (user overrides default)

$ git-pm config packages_dir ".project"
# Now: .project (project overrides user)

$ git-pm config --unset packages_dir
# Now: .vendor (back to user)

$ git-pm config --unset --global packages_dir
# Now: .git-packages (back to default)
```

---

## List Output

```
azure_devops_pat=(empty) (default)
cache_dir=/tmp/cache (user)
git_protocol={} (default)
packages_dir=.deps (project)
url_patterns={} (default)
```

Source indicators:
- `(default)` - Built-in default value
- `(user)` - From `~/.git-pm/config`
- `(project)` - From `git-pm.config`

---

## Common Tasks

**Change install directory:**
```bash
git-pm config packages_dir ".deps"
```

**Custom cache location:**
```bash
git-pm config --global cache_dir "/mnt/ssd/cache"
```

**Review settings:**
```bash
git-pm config --list
```

**Reset to default:**
```bash
git-pm config --unset packages_dir
git-pm config --unset --global packages_dir
```

---

## Features

✅ Auto-creates config files  
✅ Validates keys (helpful errors)  
✅ Silent unset of missing keys  
✅ Pure value output for GET  
✅ Source info in LIST  
✅ JSON format preserved  
✅ Works with existing configs  

---

## Version

Introduced in **git-pm v0.4.0**
