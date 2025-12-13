# Path Resolution Problem - Complete Guide

## 🔴 The Exact Problem You Described

### Development: Working on PackageB

```
workspace/
├── .git-packages/           ← Dependencies installed here
│   └── packageA/
├── packageB/                ← Package you're developing
│   ├── main.tf
│   └── git-pm.yaml
└── projectC/
    └── other stuff...
```

From `workspace/packageB/main.tf`:
```hcl
module "a" {
  source = "../.git-packages/packageA"  # ✅ Works
}
```

### Consumption: ProjectC Uses PackageB

```
projectC/
└── .git-packages/
    ├── packageA/
    └── packageB/
        └── main.tf          ← Same code, different location
```

From `projectC/.git-packages/packageB/main.tf`:
```hcl
module "a" {
  source = "../.git-packages/packageA"  # ❌ BREAKS!
  # Actually looks for: .git-packages/.git-packages/packageA
}
```

**The Problem:** The SAME relative path `../.git-packages/packageA` works in one scenario but not the other!

## ⚠️ Why This Happens

The relative path is calculated from the file location:

**Development:**
```
FROM: workspace/packageB/main.tf
TO:   workspace/.git-packages/packageA
PATH: ../.git-packages/packageA  ✅
```

**Consumption:**
```
FROM: projectC/.git-packages/packageB/main.tf
TO:   projectC/.git-packages/packageA
PATH: ../packageA  (NOT ../.git-packages/packageA!)
```

## ✅ Solution Overview

**You need THREE approaches** depending on the tool:

| Tool | Solution | Why |
|------|----------|-----|
| **Terraform** | Symlinks | Can't use env vars in `source` |
| **Scripts** | Environment variables | Dynamic, flexible |
| **CI/CD** | Environment variables | Portable, clear |

## 🔗 Solution 1: Symlinks (For Terraform)

### What git-pm Does

After installation, git-pm creates symlinks **inside each package**:

```
projectC/
└── .git-packages/
    ├── packageA/
    └── packageB/
        ├── main.tf
        └── .git-packages/           ← Auto-created!
            └── packageA -> ../../packageA
```

### How This Solves It

**During Development:**
```
workspace/packageB/.git-packages/packageA
→ Real directory (from git-pm install in packageB)
```

**During Consumption:**
```
projectC/.git-packages/packageB/.git-packages/packageA
→ Symlink to ../../packageA (created by git-pm)
→ Resolves to projectC/.git-packages/packageA ✅
```

### Your Code (Works in Both!)

```hcl
# packageB/main.tf
module "package_a" {
  source = ".git-packages/packageA"  # NOT ../.git-packages/packageA
}
```

**Key Change:** Use `.git-packages/` (relative to current file) instead of `../.git-packages/` (relative to parent)

### Why This Works

**Development:**
```
packageB/main.tf references .git-packages/packageA
→ workspace/packageB/.git-packages/packageA (real directory) ✅
```

**Consumption:**
```
packageB/main.tf references .git-packages/packageA  
→ projectC/.git-packages/packageB/.git-packages/packageA (symlink)
→ Points to ../../packageA
→ Resolves to projectC/.git-packages/packageA ✅
```

## 🌍 Solution 2: Environment Variables (For Scripts)

### What git-pm Generates

After `git-pm install`, you get `.git-pm.env`:

```bash
# git-pm environment configuration
export GIT_PM_PACKAGES_DIR="/absolute/path/to/.git-packages"
export GIT_PM_PROJECT_ROOT="/absolute/path/to/project"
export GIT_PM_REL_PACKAGES_DIR="../"  # Relative from any package to packages dir

# Individual packages
export GIT_PM_PACKAGE_PACKAGEA="/absolute/path/to/.git-packages/packageA"
export GIT_PM_PACKAGE_PACKAGEB="/absolute/path/to/.git-packages/packageB"
```

### Usage in Scripts

#### Bash/Shell Scripts
```bash
#!/bin/bash
# deploy.sh

# Load environment
source .git-pm.env

# Use absolute paths - works everywhere!
terraform -chdir="$GIT_PM_PACKAGE_PACKAGEB" init
terraform -chdir="$GIT_PM_PACKAGE_PACKAGEB" plan

# Copy files from dependencies
cp "$GIT_PM_PACKAGE_PACKAGEA/config.yaml" ./
```

#### Python Scripts
```python
#!/usr/bin/env python3
import os
import subprocess

# Load from environment
packages_dir = os.environ.get('GIT_PM_PACKAGES_DIR')
if not packages_dir:
    # Parse .git-pm.env file
    with open('.git-pm.env') as f:
        for line in f:
            if line.startswith('export GIT_PM_PACKAGES_DIR='):
                packages_dir = line.split('=')[1].strip().strip('"')
                break

# Use absolute paths
packageA_path = os.path.join(packages_dir, 'packageA')
packageB_path = os.path.join(packages_dir, 'packageB')

# Run terraform with absolute path
subprocess.run(['terraform', '-chdir', packageB_path, 'init'])
```

#### Makefile
```makefile
# Load environment variables
include .git-pm.env

.PHONY: deploy
deploy:
	cd $(GIT_PM_PACKAGE_PACKAGEB) && terraform init
	cd $(GIT_PM_PACKAGE_PACKAGEB) && terraform apply

.PHONY: test
test:
	cd $(GIT_PM_PACKAGE_PACKAGEA) && go test ./...
```

## 📝 Solution 3: Terraform Variables (Alternative)

Since Terraform can't use environment variables in `source`, but CAN use them in variables, here's an alternative approach:

### Generate Terraform Variables

```bash
# Source environment
source .git-pm.env

# Generate auto.tfvars file
git-pm-generate-tfvars > packages.auto.tfvars
```

**Generated packages.auto.tfvars:**
```hcl
# Auto-generated package paths
git_pm_packages_dir = "/absolute/path/to/.git-packages"
packagea_path = "/absolute/path/to/.git-packages/packageA"
packageb_path = "/absolute/path/to/.git-packages/packageB"
```

### Use in Your Code

**Define variables:**
```hcl
# packageB/variables.tf
variable "packagea_path" {
  description = "Path to packageA (provided by git-pm)"
  type        = string
}
```

**Use in modules:**
```hcl
# packageB/main.tf
# Can't use variable in source directly, but can in data sources
data "local_file" "packagea_config" {
  filename = "${var.packagea_path}/config.yaml"
}

# Or pass to child modules
module "submodule" {
  source = "./submodule"
  
  packagea_path = var.packagea_path
}
```

## 🎯 Recommended Approach: Use Symlinks

**For your specific case (Terraform modules), use the symlink approach:**

### Step 1: Update Your Package Code

Change from:
```hcl
# ❌ OLD: packageB/main.tf
module "a" {
  source = "../.git-packages/packageA"  # Breaks in consumption
}
```

To:
```hcl
# ✅ NEW: packageB/main.tf
module "a" {
  source = ".git-packages/packageA"  # Works everywhere via symlinks
}
```

### Step 2: Install with git-pm

```bash
# In development
cd packageB
git-pm install
# Creates: packageB/.git-packages/packageA (real directory)

# In consumption
cd projectC
git-pm install
# Creates: projectC/.git-packages/packageB/.git-packages/packageA (symlink)
```

### Step 3: Verify

```bash
# Check symlinks
$ ls -la .git-packages/packageB/.git-packages/
packageA -> ../../packageA  ✅

# Test Terraform
$ cd .git-packages/packageB
$ terraform init
Initializing modules...
- package_a in .git-packages/packageA  ✅
```

## 📊 Complete Example: Your Setup

### Your Workspace Structure

```
workspace/
├── .git-packages/               # Shared dependencies
│   ├── aws_account/
│   └── aws_ou/
├── azure_bootstrap/             # Package you're developing
│   ├── main.tf
│   └── git-pm.yaml
└── my-project/                  # Project that uses azure_bootstrap
    └── main.tf
```

### Step 1: Update azure_bootstrap/main.tf

```hcl
# azure_bootstrap/main.tf

# ❌ OLD (breaks when consumed)
# module "aws_account" {
#   source = "../.git-packages/aws_account"
# }

# ✅ NEW (works everywhere)
module "aws_account" {
  source = ".git-packages/aws_account"
}

module "aws_ou" {
  source = ".git-packages/aws_ou"
}
```

### Step 2: Development

```bash
cd workspace/azure_bootstrap
git-pm install

# This creates:
# workspace/azure_bootstrap/.git-packages/
#   ├── aws_account/
#   └── aws_ou/

terraform init  # ✅ Works
terraform plan
```

### Step 3: Consumption

```bash
cd workspace/my-project

# git-pm.yaml
cat > git-pm.yaml << 'EOF'
packages:
  azure_bootstrap:
    repo: dev.azure.com/.../tf-modules-iac
    path: azure_bootstrap
    ref:
      type: tag
      value: v1.0.28
EOF

git-pm install

# This creates:
# workspace/my-project/.git-packages/
#   ├── aws_account/        (resolved dependency)
#   ├── aws_ou/             (resolved dependency)
#   └── azure_bootstrap/
#       └── .git-packages/  (symlinks created by git-pm!)
#           ├── aws_account -> ../../aws_account
#           └── aws_ou -> ../../aws_ou

# Use it
cat > main.tf << 'EOF'
module "bootstrap" {
  source = "./.git-packages/azure_bootstrap"
}
EOF

terraform init  # ✅ Works! azure_bootstrap's modules resolve via symlinks
```

## 🔧 Using Environment Variables for Scripts

While Terraform uses symlinks, you can ALSO use environment variables for scripts:

```bash
#!/bin/bash
# workspace/scripts/deploy-all.sh

# Load environment
source .git-pm.env

# Deploy packageA
echo "Deploying PackageA..."
terraform -chdir="$GIT_PM_PACKAGE_AWS_ACCOUNT" init
terraform -chdir="$GIT_PM_PACKAGE_AWS_ACCOUNT" apply -auto-approve

# Deploy packageB (which depends on A)
echo "Deploying Azure Bootstrap..."
terraform -chdir="$GIT_PM_PACKAGE_AZURE_BOOTSTRAP" init
terraform -chdir="$GIT_PM_PACKAGE_AZURE_BOOTSTRAP" apply -auto-approve
```

## 🎓 Why Can't Terraform Use Environment Variables in source?

Terraform's `source` parameter is evaluated at **parse time**, not runtime:

```hcl
# ❌ This does NOT work
module "a" {
  source = "${env.GIT_PM_PACKAGES_DIR}/packageA"
}

# ❌ This also does NOT work
variable "packages_dir" { default = "/path" }
module "a" {
  source = "${var.packages_dir}/packageA"
}
```

**Why:** Terraform needs to know the source location before it can evaluate variables or expressions.

**Solution:** Use symlinks so the relative path is always correct.

## 📋 Quick Reference

### For Terraform Modules
```hcl
# Always use .git-packages/ prefix (not ../.git-packages/)
module "dep" {
  source = ".git-packages/dependency"
}
```
✅ **Automatic** - git-pm creates symlinks

### For Bash Scripts
```bash
source .git-pm.env
terraform -chdir="$GIT_PM_PACKAGE_NAME" apply
```
✅ **Manual** - source environment file first

### For Python
```python
import os
packages_dir = os.environ['GIT_PM_PACKAGES_DIR']
package_path = os.path.join(packages_dir, 'package_name')
```
✅ **Manual** - parse or load environment

### For CI/CD
```yaml
steps:
  - run: source .git-pm.env
  - run: terraform -chdir=$GIT_PM_PACKAGE_X apply
```
✅ **Manual** - export variables in pipeline

## ✅ Verification Checklist

After updating your code:

1. **Update source paths**
   ```bash
   # Find and replace in your packages
   find . -name "*.tf" -exec sed -i 's|\.\./\.git-packages/|.git-packages/|g' {} +
   ```

2. **Test in development**
   ```bash
   cd packageB
   git-pm install
   terraform init  # Should work
   ```

3. **Test in consumption**
   ```bash
   cd projectC
   git-pm install  # Creates symlinks
   terraform init  # Should work
   ```

4. **Check symlinks**
   ```bash
   ls -la .git-packages/packageB/.git-packages/
   # Should show symlinks to sibling packages
   ```

5. **Test scripts**
   ```bash
   source .git-pm.env
   echo $GIT_PM_PACKAGES_DIR  # Should show absolute path
   ```

## 📝 Summary

**Problem:** `../.git-packages/packageA` works in dev, breaks in consumption  
**Root Cause:** Different relative paths in different scenarios  
**Solution for Terraform:** Use `.git-packages/packageA` + automatic symlinks  
**Solution for Scripts:** Use environment variables from `.git-pm.env`  
**Result:** Works everywhere! ✅

---

**Key Changes to Make:**

1. Update module sources from `../.git-packages/X` to `.git-packages/X`
2. Run `git-pm install` to create symlinks
3. Use `.git-pm.env` for scripts (optional)

**Files Generated:**
- `.git-pm.env` - Environment variables
- `.git-packages/*/git-packages/*` - Symlinks to dependencies

That's it! The symlinks make the path resolution work automatically.
