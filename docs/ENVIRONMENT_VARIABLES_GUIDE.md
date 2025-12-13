# Dependency Path Resolution - Complete Solution

## 🔴 The Core Problem

When PackageB depends on PackageA, the relative path differs between development and consumption:

### During Development
```
packageB/                      # Working directory
├── main.tf
├── git-pm.yaml
└── .git-packages/
    └── packageA/
```

**Path from packageB/main.tf:** `.git-packages/packageA` ✅

### When Consumed by ProjectC
```
projectC/
└── .git-packages/
    ├── packageA/
    └── packageB/
        └── main.tf
```

**Same path from packageB/main.tf:** `.git-packages/packageA`  
**Resolves to:** `projectC/.git-packages/packageB/.git-packages/packageA` ❌

**The problem:** No single relative path works in both scenarios!

## ✅ Solution: Dual Approach

git-pm now provides **TWO complementary solutions**:

1. **Symlinks** - For Terraform and path-based references
2. **Environment Variables** - For scripts and dynamic references

## 🔗 Solution 1: Symlinks (Automatic)

### What git-pm Does

After installation, git-pm creates `.git-packages/` inside each package with symlinks to its dependencies:

```
projectC/
└── .git-packages/
    ├── packageA/
    │   └── main.tf
    └── packageB/
        ├── main.tf
        └── .git-packages/              ← Auto-created
            └── packageA -> ../../packageA
```

### How It Works

**During Development:**
```
packageB/.git-packages/packageA  → Real directory ✅
```

**When Consumed:**
```
projectC/.git-packages/packageB/.git-packages/packageA  → Symlink to ../../packageA ✅
```

### Usage (Terraform)

```hcl
# packageB/main.tf - Works in both scenarios!
module "package_a" {
  source = ".git-packages/packageA"
}
```

### Pros & Cons

✅ **Pros:**
- Works with Terraform (follows symlinks)
- No code changes needed
- Completely transparent
- Works offline

❌ **Cons:**
- Requires symlink support (Windows 10+)
- Not visible in git status (symlinks in .git-packages)

## 🌍 Solution 2: Environment Variables (New!)

### What git-pm Does

After installation, git-pm generates `.git-pm.env` with package locations:

```bash
# .git-pm.env (auto-generated)
export GIT_PM_PACKAGES_DIR="/absolute/path/to/projectC/.git-packages"
export GIT_PM_PROJECT_ROOT="/absolute/path/to/projectC"

# Individual package paths
export GIT_PM_PACKAGE_PACKAGEA="/absolute/path/to/projectC/.git-packages/packageA"
export GIT_PM_PACKAGE_PACKAGEB="/absolute/path/to/projectC/.git-packages/packageB"
```

### Usage in Scripts

#### Bash/Shell
```bash
# Source the environment file
source .git-pm.env

# Use in your scripts
echo "Packages at: $GIT_PM_PACKAGES_DIR"
cd "$GIT_PM_PACKAGE_PACKAGEB"
```

#### Python
```python
import os
from pathlib import Path

# Load from environment (if sourced)
packages_dir = os.environ.get('GIT_PM_PACKAGES_DIR')

# Or parse the file directly
with open('.git-pm.env') as f:
    for line in f:
        if line.startswith('export GIT_PM_PACKAGES_DIR='):
            packages_dir = line.split('=')[1].strip().strip('"')
            break

packageA_path = Path(packages_dir) / 'packageA'
```

#### Make
```makefile
# Load environment variables
include .git-pm.env

.PHONY: test
test:
	@echo "Testing with packageA at: $(GIT_PM_PACKAGE_PACKAGEA)"
	cd $(GIT_PM_PACKAGE_PACKAGEA) && make test
```

#### Node.js
```javascript
// Load .env file
require('dotenv').config({ path: '.git-pm.env' });

const packagesDir = process.env.GIT_PM_PACKAGES_DIR;
const packageAPath = process.env.GIT_PM_PACKAGE_PACKAGEA;

console.log(`PackageA at: ${packageAPath}`);
```

### Dynamic Path Resolution

For tools that don't support environment variables in config, use a wrapper:

```bash
#!/bin/bash
# run-terraform.sh

source .git-pm.env

# Now any script can access $GIT_PM_PACKAGES_DIR
terraform "$@"
```

### Pros & Cons

✅ **Pros:**
- Works with any tool/language
- Absolute paths (no ambiguity)
- Easy to debug
- Visible in shell (env vars)

❌ **Cons:**
- Requires sourcing .git-pm.env
- Terraform can't use env vars in source paths
- Additional setup step

## 📊 Complete Solution Matrix

| Use Case | Solution | How |
|----------|----------|-----|
| **Terraform modules** | Symlinks ✅ | Automatic, no changes needed |
| **Shell scripts** | Environment vars ✅ | `source .git-pm.env` |
| **Python imports** | Environment vars ✅ | Parse or load env |
| **Node.js requires** | Environment vars ✅ | Use dotenv |
| **Makefiles** | Environment vars ✅ | `include .git-pm.env` |
| **Docker builds** | Environment vars ✅ | Pass via `-e` flag |
| **CI/CD** | Environment vars ✅ | Export in pipeline |

## 🎯 Recommended Approach by Tool

### For Terraform (Use Symlinks)

```hcl
# packageB/main.tf
module "package_a" {
  source = ".git-packages/packageA"  # Symlink approach
}
```

**No additional setup required!** git-pm handles it automatically.

### For Scripts (Use Environment Variables)

```bash
#!/bin/bash
# deploy.sh

# Load package locations
source .git-pm.env

# Use absolute paths
terraform -chdir="$GIT_PM_PACKAGE_PACKAGEB" init
terraform -chdir="$GIT_PM_PACKAGE_PACKAGEB" apply
```

### For Multi-Tool Projects (Use Both)

```
project/
├── .git-pm.env           ← Environment variables
├── deploy.sh             ← Uses env vars
└── .git-packages/
    ├── packageA/
    └── packageB/
        ├── main.tf       ← Uses symlinks
        └── .git-packages/
            └── packageA -> ../../packageA
```

## 🔧 Installation Output

```bash
$ git-pm install
🚀 git-pm install (dependency resolution)
✓ Git detected: git version 2.52.0
📋 Loading configuration...
📄 Loading manifest...
🔍 Discovering dependencies...
📦 Discovering azure_bootstrap...
  Found 2 dependencies
   Found 3 total packages
📦 Planning installation order...
   Order: aws_common -> azure_common -> azure_bootstrap
📥 Installing 3 package(s)...
📦 Installing aws_common...
📦 Installing azure_common...
📦 Installing azure_bootstrap...
💾 Saving lockfile...
🔗 Creating dependency symlinks...
  ✓ azure_bootstrap/aws_common -> aws_common
  ✓ azure_bootstrap/azure_common -> azure_common
📝 Generating environment file...
  ✓ Created .git-pm.env
✅ Installation complete! (3/3 packages)
```

## 📋 Generated Files

### .git-pm.env
```bash
# git-pm environment configuration
# Source this file in your shell: source .git-pm.env
# Or use in scripts: $(cat .git-pm.env | grep GIT_PM_PACKAGES_DIR | cut -d= -f2)

export GIT_PM_PACKAGES_DIR="/Users/warrenn/projects/myapp/.git-packages"
export GIT_PM_PROJECT_ROOT="/Users/warrenn/projects/myapp"

# Individual package paths
export GIT_PM_PACKAGE_AWS_COMMON="/Users/warrenn/projects/myapp/.git-packages/aws_common"
export GIT_PM_PACKAGE_AZURE_COMMON="/Users/warrenn/projects/myapp/.git-packages/azure_common"
export GIT_PM_PACKAGE_AZURE_BOOTSTRAP="/Users/warrenn/projects/myapp/.git-packages/azure_bootstrap"
```

### Directory Structure
```
projectC/
├── .git-pm.env                              ← Environment variables
├── git-pm.yaml
├── git-pm.lock
└── .git-packages/
    ├── aws_common/
    │   └── main.tf
    ├── azure_common/
    │   └── main.tf
    └── azure_bootstrap/
        ├── main.tf
        └── .git-packages/                   ← Symlinks
            ├── aws_common -> ../../aws_common
            └── azure_common -> ../../azure_common
```

## 🎓 Advanced Usage

### Shell Integration

Add to your `.bashrc` or `.zshrc`:

```bash
# Auto-load git-pm environment when entering project
cd() {
    builtin cd "$@"
    if [ -f .git-pm.env ]; then
        source .git-pm.env
        echo "✓ Loaded git-pm environment"
    fi
}
```

### CI/CD Integration

#### GitHub Actions
```yaml
- name: Setup git-pm environment
  run: |
    source .git-pm.env
    echo "GIT_PM_PACKAGES_DIR=$GIT_PM_PACKAGES_DIR" >> $GITHUB_ENV
    
- name: Deploy
  run: |
    terraform -chdir="$GIT_PM_PACKAGE_AZURE_BOOTSTRAP" init
    terraform -chdir="$GIT_PM_PACKAGE_AZURE_BOOTSTRAP" apply
```

#### GitLab CI
```yaml
variables:
  GIT_PM_ENV_FILE: .git-pm.env

before_script:
  - source $GIT_PM_ENV_FILE

deploy:
  script:
    - terraform -chdir="$GIT_PM_PACKAGE_AZURE_BOOTSTRAP" apply
```

#### Azure DevOps
```yaml
steps:
- bash: |
    source .git-pm.env
    echo "##vso[task.setvariable variable=GIT_PM_PACKAGES_DIR]$GIT_PM_PACKAGES_DIR"
  displayName: Load git-pm environment

- bash: |
    terraform -chdir="$GIT_PM_PACKAGE_AZURE_BOOTSTRAP" apply
  displayName: Deploy
```

### Docker Integration

```dockerfile
# Dockerfile
FROM hashicorp/terraform:latest

WORKDIR /workspace

# Copy git-pm environment
COPY .git-pm.env .
COPY .git-packages .git-packages

# Load environment and use it
RUN . ./.git-pm.env && \
    terraform -chdir="$GIT_PM_PACKAGES_DIR/azure_bootstrap" init
```

Or with docker run:
```bash
# Export variables from file
export $(cat .git-pm.env | xargs)

# Pass to container
docker run -e GIT_PM_PACKAGES_DIR \
           -v "$GIT_PM_PACKAGES_DIR:/packages" \
           terraform:latest
```

### Custom Wrapper Script

```bash
#!/bin/bash
# terraform-with-git-pm.sh
# Wrapper that loads git-pm environment before running terraform

set -e

# Load git-pm environment
if [ ! -f .git-pm.env ]; then
    echo "Error: .git-pm.env not found. Run 'git-pm install' first."
    exit 1
fi

source .git-pm.env

# Run terraform with all arguments
terraform "$@"
```

Usage:
```bash
./terraform-with-git-pm.sh init
./terraform-with-git-pm.sh plan
./terraform-with-git-pm.sh apply
```

## 📝 .gitignore Recommendations

```gitignore
# git-pm
.git-packages/
git-pm.lock
.git-pm.env        # Environment file (regenerated on install)
```

**Note:** `.git-pm.env` contains absolute paths specific to your machine, so it should not be committed.

## 🎯 Your Configuration

With your actual setup:

### git-pm.yaml
```yaml
packages:
  azure_bootstrap:
    repo: dev.azure.com/bridgewaybentech/Platform Engineering/_git/tf-modules-iac
    path: azure_bootstrap
    ref:
      type: tag
      value: v1.0.28
  
  aws_account:
    repo: dev.azure.com/bridgewaybentech/Platform Engineering/_git/tf-modules-iac
    path: aws/account
    ref:
      type: tag
      value: v1.0.28
```

### After Installation

**Generated .git-pm.env:**
```bash
export GIT_PM_PACKAGES_DIR="/path/to/your/project/.git-packages"
export GIT_PM_PROJECT_ROOT="/path/to/your/project"

export GIT_PM_PACKAGE_AZURE_BOOTSTRAP="/path/to/your/project/.git-packages/azure_bootstrap"
export GIT_PM_PACKAGE_AWS_ACCOUNT="/path/to/your/project/.git-packages/aws_account"
```

**Symlinks created:**
```
.git-packages/
├── aws_account/
├── aws_ou/
└── azure_bootstrap/
    ├── main.tf
    └── .git-packages/
        ├── aws_account -> ../../aws_account
        └── aws_ou -> ../../aws_ou
```

### Usage in azure_bootstrap

**Terraform (use symlinks):**
```hcl
# azure_bootstrap/main.tf
module "aws_account" {
  source = ".git-packages/aws_account"  # Works via symlink ✅
}
```

**Scripts (use environment):**
```bash
#!/bin/bash
# azure_bootstrap/deploy.sh

source ../.git-pm.env  # Load from parent project

terraform init
terraform plan -var-file="$GIT_PM_PACKAGE_AWS_ACCOUNT/defaults.tfvars"
```

## 🔍 Debugging

### Check Symlinks
```bash
$ ls -la .git-packages/azure_bootstrap/.git-packages/
total 0
lrwxr-xr-x  aws_account -> ../../aws_account
lrwxr-xr-x  aws_ou -> ../../aws_ou
```

### Check Environment
```bash
$ source .git-pm.env
$ echo $GIT_PM_PACKAGES_DIR
/Users/warrenn/projects/myapp/.git-packages

$ env | grep GIT_PM
GIT_PM_PACKAGES_DIR=/Users/warrenn/projects/myapp/.git-packages
GIT_PM_PROJECT_ROOT=/Users/warrenn/projects/myapp
GIT_PM_PACKAGE_AZURE_BOOTSTRAP=/Users/warrenn/projects/myapp/.git-packages/azure_bootstrap
```

### Test Terraform Resolution
```bash
$ cd .git-packages/azure_bootstrap
$ terraform init
Initializing modules...
- aws_account in .git-packages/aws_account    ← Via symlink ✅

$ terraform providers
Providers required by configuration:
.
├── provider[registry.terraform.io/hashicorp/aws]
└── module.aws_account
    └── provider[registry.terraform.io/hashicorp/aws]
```

## 📊 Comparison

| Approach | Best For | Setup | Portability |
|----------|----------|-------|-------------|
| **Symlinks** | Terraform, path-based tools | Automatic | Platform-dependent (Windows 10+) |
| **Environment Variables** | Scripts, dynamic paths | Manual source | Cross-platform |
| **Both** | Production systems | Combined | Maximum compatibility |

## ✅ Best Practices

### 1. Use Symlinks for Terraform
```hcl
# Always use relative .git-packages/ path
module "dep" {
  source = ".git-packages/dependency"
}
```

### 2. Use Environment for Scripts
```bash
# Always source environment first
source .git-pm.env
terraform -chdir="$GIT_PM_PACKAGE_X" apply
```

### 3. Document in README
```markdown
## Setup

1. Install dependencies:
   ```bash
   git-pm install
   ```

2. For scripts, load environment:
   ```bash
   source .git-pm.env
   ```
```

### 4. Add to .gitignore
```gitignore
.git-packages/
.git-pm.env
git-pm.lock
```

## 📝 Summary

**Problem:** Relative paths break between development and consumption  
**Solution 1:** Auto-create symlinks for Terraform  
**Solution 2:** Generate environment file for scripts  
**Result:** Works in all scenarios with all tools  

## 🎉 Benefits

- ✅ **Terraform:** Works seamlessly with symlinks
- ✅ **Scripts:** Use environment variables for absolute paths
- ✅ **CI/CD:** Export variables in pipelines
- ✅ **Docker:** Pass environment or mount paths
- ✅ **Universal:** Works with any tool or language

---

**Files Generated:**
- `.git-pm.env` - Environment variables with package paths
- `.git-packages/*/git-packages/*` - Symlinks to dependencies

**Commit message:**
```
Feature: Generate .git-pm.env for path resolution

In addition to symlinks, now generate .git-pm.env file with:
- GIT_PM_PACKAGES_DIR: Absolute path to .git-packages
- GIT_PM_PROJECT_ROOT: Absolute path to project root
- GIT_PM_PACKAGE_*: Individual package paths

Usage:
- Terraform: Use symlinks (automatic)
- Scripts: source .git-pm.env
- CI/CD: Export variables from .git-pm.env

Fixes: Dynamic path resolution for scripts and tools
```
