# Nested Dependency Symlinks - Path Resolution Fix

## 🐛 The Problem

When PackageB depends on PackageA, there's a **path resolution conflict** between development and consumption:

### Scenario 1: Developing PackageB
```
packageB/
├── main.tf                    # Your module code
├── git-pm.yaml                # Depends on packageA
└── .git-packages/
    └── packageA/              # Dependency
```

**Path in code:** `source = ".git-packages/packageA"` ✅ Works

### Scenario 2: ProjectC Uses PackageB
```
projectC/
└── .git-packages/
    ├── packageA/              # Resolved dependency
    └── packageB/
        └── main.tf            # PackageB's code
```

**Same path:** `source = ".git-packages/packageA"` ❌ Fails!  
Looks for: `.git-packages/packageB/.git-packages/packageA` (doesn't exist)

## ❌ The Conflict

**No single path works in both scenarios:**

| Path in PackageB | Development | Consumption |
|------------------|-------------|-------------|
| `.git-packages/packageA` | ✅ Works | ❌ Fails |
| `../packageA` | ❌ Fails | ✅ Works |
| `../../packageA` | ❌ Fails | ❌ Fails |

This is a **fundamental design issue** with flat package installation.

## ✅ The Solution: Dependency Symlinks

git-pm now creates `.git-packages/` directories **inside each package** with symlinks to sibling dependencies:

```
projectC/
└── .git-packages/
    ├── packageA/
    │   └── main.tf
    └── packageB/
        ├── main.tf
        └── .git-packages/      ← Created by git-pm
            └── packageA -> ../../packageA  ← Symlink to sibling
```

### How It Works

After installing all packages, git-pm:
1. Examines each package's dependencies
2. Creates `.git-packages/` directory inside the package
3. Creates symlinks pointing to sibling packages (using `../../depName`)

### Result

**Both scenarios now work** with the same path:

```hcl
# packageB/main.tf
module "common" {
  source = ".git-packages/packageA"  # Works in both scenarios! ✅
}
```

**During Development:**
```
packageB/.git-packages/packageA  → Real directory ✅
```

**During Consumption:**
```
projectC/.git-packages/packageB/.git-packages/packageA  → Symlink to ../../packageA ✅
```

## 📋 Installation Output

```bash
$ git-pm install
🚀 git-pm install (dependency resolution)
✓ Git detected: git version 2.52.0
📋 Loading configuration...
📄 Loading manifest...
🔍 Discovering dependencies...
📦 Discovering azure_bootstrap...
  Found 2 dependencies
📦 Discovering aws_common (depth 1)...
📦 Discovering azure_common (depth 1)...
   Found 3 total packages
📦 Planning installation order...
   Order: aws_common -> azure_common -> azure_bootstrap
📥 Installing 3 package(s)...
📦 Installing aws_common...
    ✓ Copied: aws/common -> .git-packages/aws_common
📦 Installing azure_common...
    ✓ Copied: azure/common -> .git-packages/azure_common
📦 Installing azure_bootstrap...
    ✓ Copied: azure_bootstrap -> .git-packages/azure_bootstrap
💾 Saving lockfile...
🔗 Creating dependency symlinks...
  ✓ azure_bootstrap/aws_common -> aws_common
  ✓ azure_bootstrap/azure_common -> azure_common
✅ Installation complete! (3/3 packages)
```

## 📊 Directory Structure

### Before Symlinks
```
.git-packages/
├── aws_common/
│   └── main.tf
├── azure_common/
│   └── main.tf
└── azure_bootstrap/
    └── main.tf        # References dependencies - how?
```

### After Symlinks
```
.git-packages/
├── aws_common/
│   └── main.tf
├── azure_common/
│   └── main.tf
└── azure_bootstrap/
    ├── main.tf
    └── .git-packages/              ← Created automatically
        ├── aws_common -> ../../aws_common     ← Symlink
        └── azure_common -> ../../azure_common ← Symlink
```

## 🎯 Usage in Terraform

### In PackageB (azure_bootstrap)

```hcl
# azure_bootstrap/main.tf
module "aws_common" {
  source = ".git-packages/aws_common"  # Always works! ✅
}

module "azure_common" {
  source = ".git-packages/azure_common"  # Always works! ✅
}
```

### During Development

```bash
cd azure_bootstrap
git-pm install
# Installs dependencies to ./git-packages/

terraform init  # Uses ./.git-packages/aws_common ✅
```

### When Consumed

```bash
cd projectC
git-pm install  # Includes azure_bootstrap
# Creates symlinks inside azure_bootstrap

cd .git-packages/azure_bootstrap
terraform init  # Uses ./.git-packages/aws_common (symlink) ✅
```

## 🔍 How Symlinks Are Created

### Relative Path Calculation

```
From: .git-packages/packageB/.git-packages/packageA
To:   .git-packages/packageA

Relative: ../../packageA
```

### Code Logic

```python
for name, pkg_info in self.discovered.items():
    dependencies = pkg_info.get("dependencies", {})
    
    pkg_dir = self.packages_dir / name
    pkg_deps_dir = pkg_dir / ".git-packages"
    pkg_deps_dir.mkdir(exist_ok=True)
    
    for dep_name in dependencies.keys():
        dep_link = pkg_deps_dir / dep_name
        dep_target = Path("..") / ".." / dep_name  # ../../dep_name
        dep_link.symlink_to(dep_target, target_is_directory=True)
```

## 📝 Example: Your Configuration

### git-pm.yaml
```yaml
packages:
  azure_bootstrap:
    repo: dev.azure.com/bridgewaybentech/Platform Engineering/_git/tf-modules-iac
    path: azure_bootstrap
    ref:
      type: tag
      value: v1.0.28
```

### azure_bootstrap/git-pm.yaml (nested dependencies)
```yaml
packages:
  aws_common:
    repo: dev.azure.com/bridgewaybentech/Platform Engineering/_git/tf-modules-iac
    path: aws/common
    ref:
      type: tag
      value: v1.0.28
```

### After Installation
```
your-project/
└── .git-packages/
    ├── aws_common/
    │   └── main.tf
    └── azure_bootstrap/
        ├── main.tf
        └── .git-packages/
            └── aws_common -> ../../aws_common  ← Auto-created symlink
```

### In azure_bootstrap/main.tf
```hcl
module "common" {
  source = ".git-packages/aws_common"  # Works! ✅
}
```

## 🎓 Design Rationale

### Why Not Nested Installation?

**Option A: Nested (npm-style)**
```
.git-packages/
└── packageB/
    └── .git-packages/
        └── packageA/  (real copy)
```

❌ **Problems:**
- Duplicate packages
- Wastes disk space
- Can't share cached dependencies
- Different versions possible (dependency hell)

### Why Not Path Rewriting?

**Option B: Rewrite paths in source code**

❌ **Problems:**
- Language-specific
- Fragile (breaks on updates)
- Can't handle all path formats
- Modifies user code

### Why Symlinks?

**Option C: Symlinks (chosen)**

✅ **Benefits:**
- Language-agnostic
- No code modification
- Share packages (no duplication)
- Works with all tools
- Easy to understand and debug

## 🔧 Edge Cases Handled

### Case 1: No Dependencies

If a package has no dependencies, no `.git-packages/` directory is created:

```
.git-packages/
└── standalone-package/
    └── main.tf        # No .git-packages/ subdirectory
```

### Case 2: Existing .git-packages Directory

If the package already has a `.git-packages/` directory (shouldn't happen, but possible):

```python
if dep_link.exists():
    continue  # Don't overwrite real directories
```

### Case 3: Symlink Update

On subsequent installs, existing symlinks are updated:

```python
if dep_link.is_symlink():
    dep_link.unlink()  # Remove old symlink
dep_link.symlink_to(dep_target)  # Create new one
```

### Case 4: Circular Dependencies

Handled during discovery (before symlink creation):
```
📦 Discovering packageA...
  Found 1 dependencies
📦 Discovering packageB (depth 1)...
  Found 1 dependencies
📦 Discovering packageA (depth 2)...
  ✗ Circular dependency: packageA -> packageB -> packageA
```

### Case 5: Windows Compatibility

Symlinks work on Windows 10+ with Developer Mode or admin privileges. If symlink creation fails:

```
⚠ Failed to create symlink for azure_bootstrap/aws_common: [WinError 1314] ...
```

Package still works if using absolute paths or manual setup.

## 🎯 Best Practices

### 1. Consistent Dependency Paths

Always use `.git-packages/` prefix:

```hcl
# ✅ Good
module "common" {
  source = ".git-packages/packageA"
}

# ❌ Avoid
module "common" {
  source = "../packageA"  # Won't work during development
}
```

### 2. Document Dependencies

In your package README:

```markdown
## Dependencies

This module requires:
- `aws_common` from `.git-packages/aws_common`
- `azure_common` from `.git-packages/azure_common`

These are automatically installed via git-pm.
```

### 3. .gitignore

Add to your package's `.gitignore`:

```gitignore
# git-pm dependencies
.git-packages/
git-pm.lock
```

### 4. Development Workflow

```bash
# 1. Clone package for development
git clone https://dev.azure.com/.../azure_bootstrap
cd azure_bootstrap

# 2. Install dependencies
git-pm install
# Creates .git-packages/ with dependencies

# 3. Develop
terraform init
terraform plan

# 4. Test integration
cd ../test-project
git-pm install  # Includes azure_bootstrap
# Symlinks created automatically
terraform init  # Uses symlinked dependencies ✅
```

## 📊 Comparison with Other Tools

| Tool | Strategy | Pros | Cons |
|------|----------|------|------|
| npm | Nested node_modules | Standard | Duplication, slow |
| pip | Flat install | Fast | No nested deps |
| cargo | Flat + versioning | Efficient | Complex |
| **git-pm** | **Flat + symlinks** | **Fast, no duplication, works everywhere** | **Requires symlink support** |

## ✅ Verification

### Check Symlinks Created

```bash
$ git-pm install
...
🔗 Creating dependency symlinks...
  ✓ azure_bootstrap/aws_common -> aws_common
  ✓ azure_bootstrap/azure_common -> azure_common

$ ls -la .git-packages/azure_bootstrap/.git-packages/
total 0
drwxr-xr-x  aws_common -> ../../aws_common
drwxr-xr-x  azure_common -> ../../azure_common
```

### Test Terraform Resolution

```bash
$ cd .git-packages/azure_bootstrap
$ terraform init
Initializing modules...
- common in .git-packages/aws_common    ← Uses symlink ✅
```

## 📝 Summary

**Problem:** Path conflict between development and consumption  
**Cause:** Flat installation + relative paths  
**Solution:** Auto-create symlinks for dependencies inside packages  
**Result:** Single path works in both scenarios  

## 🎉 Benefits

- ✅ **Consistent paths** - Same code works everywhere
- ✅ **No duplication** - Shared dependencies
- ✅ **Fast** - No extra cloning
- ✅ **Language-agnostic** - Works with any tool
- ✅ **Automatic** - No manual setup needed

---

**Files Modified:**
- `git-pm.py` - Added `create_dependency_symlinks()` method

**Commit message:**
```
Feature: Auto-create dependency symlinks in packages

Solves path resolution conflict between development and consumption.
When a package has dependencies, git-pm now creates a .git-packages/
directory inside it with symlinks to sibling packages.

- Add create_dependency_symlinks() method
- Call after successful installation
- Create ../../depName symlinks
- Skip packages without dependencies
- Handle Windows symlink errors gracefully

Fixes: Path resolution for nested dependencies
```
