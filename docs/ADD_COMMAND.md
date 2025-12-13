# git-pm add Command

Add or update packages in your manifest without manually editing YAML files.

## Basic Usage

```bash
python git-pm.py add <name> <repo> [options]
```

## Arguments

### Required
- `name` - Package name (how you'll reference it in your code)
- `repo` - Repository identifier (e.g., `github.com/owner/repo`)

### Optional
- `--path PATH` - Path within the repository (default: root)
- `--ref-type {tag,branch,commit}` - Reference type (default: branch)
- `--ref-value VALUE` - Tag name, branch name, or commit SHA (default: main)

## Examples

### Add from GitHub
```bash
python git-pm.py add utils github.com/company/utilities
```

Creates:
```yaml
packages:
  utils:
    repo: github.com/company/utilities
    path: ""
    ref:
      type: branch
      value: main
```

### Add with Specific Path and Tag
```bash
python git-pm.py add auth github.com/company/monorepo \
    --path packages/auth \
    --ref-type tag \
    --ref-value v2.1.0
```

Creates:
```yaml
packages:
  auth:
    repo: github.com/company/monorepo
    path: packages/auth
    ref:
      type: tag
      value: v2.1.0
```

### Add from Azure DevOps
```bash
python git-pm.py add datamodels dev.azure.com/org/project/_git/models \
    --path src/models \
    --ref-type branch \
    --ref-value develop
```

### Add from GitLab
```bash
python git-pm.py add shared gitlab.com/company/shared-libs \
    --path components \
    --ref-type tag \
    --ref-value v1.5.2
```

### Add Specific Commit
```bash
python git-pm.py add core github.com/team/core-lib \
    --ref-type commit \
    --ref-value abc123def456
```

## Common Workflows

### Add Multiple Packages
```bash
# Add authentication package
python git-pm.py add auth github.com/company/auth --path src

# Add utilities
python git-pm.py add utils github.com/company/utils --path lib

# Add data models
python git-pm.py add models dev.azure.com/org/proj/_git/models

# Install all
python git-pm.py install
```

### Update Existing Package
```bash
# Update to new version
python git-pm.py add mylib github.com/owner/mylib \
    --ref-type tag \
    --ref-value v3.0.0

# Reinstall
python git-pm.py clean
python git-pm.py install
```

### Start New Project
```bash
# Create manifest and add first package
python git-pm.py add utils github.com/company/utils

# Verify manifest was created
cat git-pm.yaml

# Install
python git-pm.py install
```

## Behavior

### Creates Manifest if Needed
If `git-pm.yaml` doesn't exist, the add command creates it:
```bash
# No manifest exists yet
python git-pm.py add mylib github.com/owner/repo
# ✓ Creates git-pm.yaml with the package
```

### Updates Existing Packages
If a package already exists, it's updated:
```bash
# First time
python git-pm.py add mylib github.com/owner/repo --ref-type tag --ref-value v1.0.0

# Update it
python git-pm.py add mylib github.com/owner/repo --ref-type tag --ref-value v2.0.0
# ✓ Overwrites the previous definition
```

## Output

When adding a new package:
```
📦 git-pm add

Adding new package: mypackage

Saving manifest to git-pm.yaml...

✓ Package 'mypackage' added to manifest

Package configuration:
  Name: mypackage
  Repo: github.com/owner/repo
  Path: src/lib
  Ref:  tag:v1.0.0

Run 'python git-pm.py install' to install the package
```

When updating an existing package:
```
📦 git-pm add

Updating existing package: mypackage

Saving manifest to git-pm.yaml...

✓ Package 'mypackage' added to manifest
...
```

## Help

View all options:
```bash
python git-pm.py add --help
```

Output:
```
usage: git-pm.py add [-h] [--path PATH] [--ref-type {tag,branch,commit}]
                     [--ref-value REF_VALUE]
                     name repo

Add a new package to git-pm.yaml or update an existing package

positional arguments:
  name                  Package name (how it will be referenced in your code)
  repo                  Repository identifier (e.g., github.com/owner/repo,
                        dev.azure.com/org/project/_git/repo)

options:
  -h, --help            show this help message and exit
  --path PATH           Path within repository to the package (default:
                        repository root)
  --ref-type {tag,branch,commit}
                        Reference type (default: branch)
  --ref-value REF_VALUE
                        Reference value - tag name, branch name, or commit SHA
                        (default: main)
```

## Tips

### Use Tags for Production
```bash
python git-pm.py add prod-lib github.com/company/lib \
    --ref-type tag \
    --ref-value v1.5.0
```
Tags are immutable and ensure reproducible builds.

### Use Branches for Development
```bash
python git-pm.py add dev-lib github.com/company/lib \
    --ref-type branch \
    --ref-value develop
```
Branches update automatically when you run `install`.

### Use Commits for Exact Pinning
```bash
python git-pm.py add fixed-lib github.com/company/lib \
    --ref-type commit \
    --ref-value abc123def456
```
Commits provide exact version pinning.

### Organize Monorepo Packages
```bash
# Add multiple packages from same repo
python git-pm.py add utils github.com/company/monorepo --path packages/utils
python git-pm.py add auth github.com/company/monorepo --path packages/auth
python git-pm.py add db github.com/company/monorepo --path packages/database
```

## Next Steps

After adding packages:

```bash
# 1. Review manifest
cat git-pm.yaml

# 2. Install packages
python git-pm.py install

# 3. Verify installation
python git-pm.py list

# 4. Use in your code
python
>>> import sys
>>> sys.path.insert(0, '.git-packages')
>>> from mypackage import something
```

## See Also

- `python git-pm.py install` - Install packages from manifest
- `python git-pm.py list` - List installed packages
- `python git-pm.py update` - Update packages to latest versions
- `python git-pm.py clean` - Remove installed packages
