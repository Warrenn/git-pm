# Dependency Resolution in git-pm

## Overview

git-pm v0.2.0 implements full dependency resolution with a unique approach: **explicit versioning only**, with automatic branch resolution to commits.

### Key Principles

1. **No Version Ranges** - All dependencies use explicit versions (tags, commits, or resolved branches)
2. **Branch Resolution** - Branches automatically resolve to latest commit SHA
3. **Independent Versioning** - Each package can be at a different commit
4. **Deterministic Installs** - Lockfile ensures reproducible builds
5. **Smart Caching** - Explicit refs cached, branches always fresh

## Version Specification

### Supported Reference Types

```yaml
packages:
  # Tag - Immutable, exact version
  pkg-a:
    ref:
      type: tag
      value: v1.2.3
  
  # Branch - Resolves to latest commit
  pkg-b:
    ref:
      type: branch
      value: main
  
  # Commit - Exact SHA
  pkg-c:
    ref:
      type: commit
      value: abc123def456789
```

### Why No Ranges?

**Traditional package managers:**
```yaml
# npm, pip, cargo style
dependencies:
  logger: ">=1.0.0,<2.0.0"  # Range
  utils: "^1.2.3"            # Caret
  helper: "~1.2.3"           # Tilde
```

**git-pm approach:**
```yaml
# Explicit only
packages:
  logger:
    ref:
      type: tag
      value: v1.5.2  # Exact version
```

**Benefits:**
- ✅ Simple - No complex version constraint solver needed
- ✅ Predictable - Know exactly what you're installing
- ✅ Fast - No need to query available versions
- ✅ Git-native - Uses git tags/branches/commits directly
- ✅ Explicit - Forces conscious version choices

**Trade-off:**
- ❌ Manual updates - Must explicitly update versions
- Mitigated by `git-pm update` for branches

## Branch Resolution

### How It Works

When a package references a branch:

1. **Fetch Latest**: Query git remote for current commit SHA
   ```bash
   git ls-remote origin refs/heads/main
   # Output: abc12345... refs/heads/main
   ```

2. **Resolve to Commit**: Store resolved commit SHA
   ```yaml
   # After resolution
   ref:
     type: commit
     value: abc12345...
   original_ref:
     type: branch
     value: main
   ```

3. **Share Resolution**: All packages referencing same branch use same commit
4. **Cache Result**: Store in lockfile for deterministic reinstalls

### Example

**Manifest:**
```yaml
packages:
  api:
    repo: github.com/company/mono
    path: packages/api
    ref:
      type: branch
      value: main
```

**api's dependencies:**
```yaml
packages:
  logger:
    repo: github.com/company/mono
    path: packages/logger
    ref:
      type: branch
      value: main
```

**Resolution:**
```bash
$ git-pm install

📦 Discovering api...
  Resolving branch 'main' to commit...
    ✓ Branch 'main' -> abc12345
  Found 1 dependencies
  📦 Discovering logger (depth 1)...
    Resolving branch 'main' to commit...
      (cached: abc12345)
```

Both `api` and `logger` install at commit `abc12345` (same snapshot of `main` branch).

### Updating Branches

```bash
git-pm update
```

**Process:**
1. Find all packages with `original_ref.type == "branch"`
2. Re-resolve each branch to latest commit
3. Force re-clone from cache (pull fresh)
4. Reinstall packages
5. Update lockfile with new commits

**Example:**
```bash
$ git-pm update

🔄 git-pm update
📋 Loading configuration...
🔄 Updating packages...
📦 Updating logger...
  Resolving branch 'main' to commit...
    ✓ Branch 'main' -> def67890  # New commit!
  Cloning ... (commit:def67890)
    ✓ Cached at commit: def67890
    ✓ Copied: packages/logger -> .git-packages/logger
✅ Updated 1 package(s)
```

## Dependency Discovery

### Recursive Discovery

**Algorithm:**
1. Start with root manifest packages
2. For each package:
   - Clone to cache (or use cached)
   - Look for `git-pm.yaml` in package root
   - If found, extract dependencies
   - Recursively discover those dependencies
3. Build complete dependency graph

**Circular Dependency Detection:**
```
api -> utils -> logger -> utils  # Circular!
```

Detected by tracking parent chain:
```python
if name in parent_chain:
    raise CircularDependencyError
```

### Cache Strategy

**For explicit refs (tags, commits):**
- Cache indefinitely
- Only clone if cache miss
- Fast repeated installs

**For branches:**
- Always pull fresh on install
- Re-resolve to latest commit
- Ensures up-to-date code

**Cache key generation:**
```python
cache_key = hash(repo + path + ref_type + ref_value)
# Example: hash("github.com/company/mono:packages/utils:tag:v1.0.0")
# Result: 6827d695b8c2a5d4
```

### Example Discovery

**Project structure:**
```
your-project/
├── git-pm.yaml          # Root manifest
└── (install creates)
    └── .git-packages/
        ├── api/
        │   └── git-pm.yaml   # api's dependencies
        ├── logger/
        └── utils/
            └── git-pm.yaml   # utils' dependencies
```

**Discovery process:**
```bash
🔍 Discovering dependencies...
📦 Discovering api...
  Cloning github.com/company/mono (tag:v3.0.0)...
    ✓ Cached at commit: abc12345
  Found git-pm.yaml with 2 dependencies
  
  📦 Discovering logger (depth 1)...
    Resolving branch 'main' to commit...
      ✓ Branch 'main' -> def67890
    Cloning github.com/company/mono (commit:def67890)...
      ✓ Cached at commit: def67890
    No dependencies found
  
  📦 Discovering utils (depth 1)...
    Cloning github.com/company/mono (tag:v2.0.0)...
      ✓ Cached at commit: ghi13579
    Found git-pm.yaml with 1 dependency
    
    📦 Discovering logger (depth 2)...
      (already discovered)

Found 3 total packages
```

## Installation Order

### Topological Sort

**Goal:** Install dependencies before dependents

**Algorithm:** Depth-first search with post-order traversal

**Example graph:**
```
api
├── logger
└── utils
    └── logger
```

**Topological order:**
```
logger -> utils -> api
```

**Why this order:**
- `logger` has no dependencies → install first
- `utils` depends on `logger` → install second
- `api` depends on both → install last

### Code

```python
def topological_sort(self):
    visited = set()
    temp_mark = set()
    order = []
    
    def visit(pkg_name):
        if pkg_name in temp_mark:
            raise Exception("Circular dependency")
        if pkg_name in visited:
            return
        
        temp_mark.add(pkg_name)
        
        # Visit dependencies first
        for dep_name in pkg_info.dependencies:
            visit(dep_name)
        
        temp_mark.remove(pkg_name)
        visited.add(pkg_name)
        order.append(pkg_name)  # Add after visiting deps
    
    for pkg_name in all_packages:
        visit(pkg_name)
    
    return order
```

## Lockfile

### Purpose

1. **Deterministic Installs** - Same versions every time
2. **Audit Trail** - Track what's installed
3. **Dependency Tree** - Show complete graph
4. **Installation Order** - Reproducible order

### Format

```json
{
  "packages": {
    "logger": {
      "repo": "github.com/company/monorepo",
      "path": "packages/logger",
      "ref": {
        "type": "commit",
        "value": "abc12345"
      },
      "original_ref": {
        "type": "branch",
        "value": "main"
      },
      "commit": "abc12345",
      "cache_key": "6827d695b8c2a5d4",
      "dependencies": [],
      "installed_at": "2024-01-15T10:30:00.123456"
    },
    "utils": {
      "repo": "github.com/company/monorepo",
      "path": "packages/utils",
      "ref": {
        "type": "tag",
        "value": "v2.0.0"
      },
      "commit": "def67890",
      "cache_key": "a1b2c3d4e5f6g7h8",
      "dependencies": ["logger"],
      "installed_at": "2024-01-15T10:30:01.234567"
    },
    "api": {
      "repo": "github.com/company/monorepo",
      "path": "packages/api",
      "ref": {
        "type": "tag",
        "value": "v3.0.0"
      },
      "commit": "ghi13579",
      "cache_key": "9i8h7g6f5e4d3c2b",
      "dependencies": ["logger", "utils"],
      "installed_at": "2024-01-15T10:30:02.345678"
    }
  },
  "installation_order": ["logger", "utils", "api"]
}
```

### Key Fields

- **ref**: Current reference (resolved for branches)
- **original_ref**: Original manifest reference (preserves branch info)
- **commit**: Actual git commit SHA installed
- **dependencies**: Direct dependencies only
- **installation_order**: Full topological order

## Comparison with Other Package Managers

### npm/pip/cargo (Traditional)

**Features:**
- ✅ Version ranges
- ✅ Automatic conflict resolution
- ✅ Central registry
- ❌ Complex constraint solving
- ❌ Registry dependence
- ❌ Potential version conflicts

**Example:**
```json
{
  "dependencies": {
    "logger": "^1.2.0",
    "utils": ">=2.0.0,<3.0.0"
  }
}
```

### git submodules (Git Native)

**Features:**
- ✅ Git-native
- ✅ Exact commits
- ❌ No dependency resolution
- ❌ Manual management
- ❌ Slow (full clones)
- ❌ Awkward workflow

**Example:**
```bash
git submodule add https://github.com/company/lib lib
git submodule update --init --recursive
```

### git-pm (Hybrid)

**Features:**
- ✅ Git-native (uses tags/branches/commits)
- ✅ Automatic dependency resolution
- ✅ Explicit versioning (no ranges)
- ✅ Fast (sparse checkout)
- ✅ Branch auto-resolution
- ✅ Simple mental model

**Example:**
```yaml
packages:
  logger:
    repo: github.com/company/monorepo
    path: packages/logger
    ref:
      type: tag
      value: v1.5.2
```

## Advanced Scenarios

### Monorepo at Single Commit

**Goal:** All packages from monorepo at same commit

**Approach:** Use commit ref for all packages

```yaml
packages:
  pkg-a:
    repo: github.com/company/mono
    path: packages/a
    ref:
      type: commit
      value: abc12345  # Same commit
  
  pkg-b:
    repo: github.com/company/mono
    path: packages/b
    ref:
      type: commit
      value: abc12345  # Same commit
```

### Independent Package Versioning

**Goal:** Different packages at different versions

**Approach:** Use tags with independent versions

```yaml
packages:
  pkg-a:
    repo: github.com/company/mono
    path: packages/a
    ref:
      type: tag
      value: v1.0.0  # Old stable version
  
  pkg-b:
    repo: github.com/company/mono
    path: packages/b
    ref:
      type: tag
      value: v2.5.0  # Latest version
```

### Development with Branches

**Goal:** Track latest development

**Approach:** Use branches, update regularly

```yaml
packages:
  experimental:
    repo: github.com/company/mono
    path: packages/experimental
    ref:
      type: branch
      value: develop  # Tracks develop branch
```

Update daily:
```bash
git-pm update  # Pulls latest develop commits
```

### Multiple Versions Side-by-Side

**Goal:** Use logger v1 and v2 simultaneously

**Approach:** Different package names

```yaml
packages:
  logger-v1:
    repo: github.com/company/mono
    path: packages/logger
    ref:
      type: tag
      value: v1.9.9
  
  logger-v2:
    repo: github.com/company/mono
    path: packages/logger
    ref:
      type: tag
      value: v2.0.0
```

Both install as separate packages:
```
.git-packages/
├── logger-v1/
└── logger-v2/
```

## Performance Characteristics

### Time Complexity

- **Discovery:** O(N) where N = total packages in dependency tree
- **Topological Sort:** O(N + E) where E = edges (dependencies)
- **Installation:** O(N × T) where T = time to clone/copy

### Space Complexity

- **Cache:** O(U) where U = unique package versions
- **Installed:** O(N) where N = total packages installed

### Optimization Strategies

1. **Sparse Checkout** - Only clone needed paths
2. **Shallow Clones** - Depth=1 for branches
3. **Shared Cache** - One cache per (repo, path, ref)
4. **Parallel Clones** - Could parallelize independent packages (future)

## Best Practices

### 1. Pin Production Dependencies

```yaml
# Good - Explicit tags
packages:
  api:
    ref:
      type: tag
      value: v1.0.0

# Avoid - Branches in production
packages:
  api:
    ref:
      type: branch
      value: main
```

### 2. Use Branches for Development

```yaml
# Development
packages:
  experimental:
    ref:
      type: branch
      value: develop
```

### 3. Commit Lockfile

```bash
git add git-pm.lock
git commit -m "Update dependencies"
```

Ensures team uses exact same versions.

### 4. Regular Updates

```bash
# Update branches weekly/daily
git-pm update
git add git-pm.lock
git commit -m "Update branch dependencies"
```

### 5. Document Breaking Changes

When updating major versions, document in PR:
```markdown
## Breaking Changes

Updated `utils` from v1.9.0 to v2.0.0:
- New API for `parse()` function
- Removed deprecated `old_parse()`
```

## Future Enhancements

### Possible Additions

1. **Parallel Installation** - Install independent packages simultaneously
2. **Integrity Checking** - SHA256 hashes in lockfile
3. **Offline Mode** - Install from cache only
4. **Lock File Validation** - Verify installed matches lockfile
5. **Dependency Graphs** - Visualize dependency tree
6. **Version Pinning Commands** - `git-pm pin <pkg> <version>`

### Not Planned

- ❌ Version ranges - Explicit only
- ❌ Central registry - Git-native only
- ❌ Automatic conflict resolution - Not needed with explicit versions

## Troubleshooting

### Circular Dependencies

**Error:**
```
✗ Circular dependency: api -> utils -> logger -> utils
```

**Solution:** Refactor to remove cycle or use local overrides during development.

### Stale Branches

**Issue:** Branch not updating

**Solution:**
```bash
# Force update
git-pm clean
git-pm install

# Or just update
git-pm update
```

### Cache Issues

**Issue:** Old cached version

**Solution:**
```bash
# Clear cache
rm -rf ~/.cache/git-pm/
git-pm install
```

### Authentication

**Issue:** Cannot access private repos

**Solution:**
```bash
# Use SSH keys
git config --global url."git@github.com:".insteadOf "https://github.com/"

# Or use tokens
export GIT_PM_TOKEN_github_com="ghp_token"
export AZURE_DEVOPS_PAT="ado_token"
```

## Summary

git-pm's dependency resolution provides:

✅ **Simple** - No complex version constraints  
✅ **Predictable** - Exact versions, no surprises  
✅ **Git-native** - Uses git primitives directly  
✅ **Fast** - Smart caching with sparse checkout  
✅ **Flexible** - Tags, branches, commits all supported  
✅ **Deterministic** - Lockfile ensures reproducibility  

Perfect for monorepos, Terraform modules, and shared libraries where explicit control is preferred over automatic resolution.
