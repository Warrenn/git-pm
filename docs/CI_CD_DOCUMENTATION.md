# CI/CD Documentation

## 📋 Overview

This document covers integrating git-pm into CI/CD pipelines, including authentication methods for various Git providers, configuration options, and best practices for seamless local and pipeline development.

## 🔐 Authentication Methods

git-pm supports multiple authentication methods to work across different environments and Git providers.

### Authentication Priority

When resolving repository URLs, git-pm checks authentication sources in this order:

| Priority | Method | Scope | Token in URL? | Best For |
|----------|--------|-------|---------------|----------|
| 1 | `AZURE_DEVOPS_PAT` | Azure DevOps | Yes | Simple setup |
| 2 | `SYSTEM_ACCESSTOKEN` | Azure DevOps | No | Azure Pipelines (recommended) |
| 3 | `GIT_PM_TOKEN_{domain}` | Any provider | Yes | Multi-provider setups |
| 4 | Config `azure_devops_pat` | Azure DevOps | Yes | Project-specific PATs |
| 5 | Config `git_protocol` | Any | N/A | Protocol selection |
| 6 | SSH auto-detection | Any | N/A | Local development |

### Environment Variables

#### `AZURE_DEVOPS_PAT`

Personal Access Token for Azure DevOps. Token is embedded directly in the URL.

```bash
export AZURE_DEVOPS_PAT="your-pat-token"
```

**Scope required:** Code (Read)

**URL generated:**
```
https://{PAT}@dev.azure.com/{org}/{project}/_git/{repo}
```

⚠️ **Note:** Token appears in git command output and logs (masked in Azure Pipelines).

---

#### `SYSTEM_ACCESSTOKEN`

Azure Pipelines system token. Uses git's `http.extraheader` for bearer authentication.

```bash
export SYSTEM_ACCESSTOKEN="$(System.AccessToken)"
```

**URL generated:**
```
https://dev.azure.com/{org}/{project}/_git/{repo}
```

**Git config set automatically:**
```bash
git config --global http.https://dev.azure.com/.extraheader "AUTHORIZATION: bearer {token}"
```

✅ **Recommended for Azure Pipelines** - Token never appears in URLs or logs.

---

#### `GIT_PM_TOKEN_{domain}`

Generic token for any Git provider. Domain dots are replaced with underscores.

| Provider | Environment Variable |
|----------|---------------------|
| GitHub | `GIT_PM_TOKEN_github_com` |
| GitLab | `GIT_PM_TOKEN_gitlab_com` |
| Bitbucket | `GIT_PM_TOKEN_bitbucket_org` |
| Azure DevOps | `GIT_PM_TOKEN_dev_azure_com` |
| Self-hosted | `GIT_PM_TOKEN_git_mycompany_com` |

**Examples:**

```bash
# GitHub
export GIT_PM_TOKEN_github_com="ghp_xxxxxxxxxxxx"
# URL: https://{token}@github.com/{owner}/{repo}.git

# GitLab
export GIT_PM_TOKEN_gitlab_com="glpat-xxxxxxxxxxxx"
# URL: https://oauth2:{token}@gitlab.com/{owner}/{repo}.git

# Bitbucket
export GIT_PM_TOKEN_bitbucket_org="app-password-here"
# URL: https://oauth2:{token}@bitbucket.org/{owner}/{repo}.git

# Self-hosted GitLab
export GIT_PM_TOKEN_gitlab_mycompany_com="glpat-xxxxxxxxxxxx"
# URL: https://oauth2:{token}@gitlab.mycompany.com/{owner}/{repo}.git
```

---

### Provider-Specific Setup

#### GitHub

**Token Type:** Personal Access Token (classic) or Fine-grained token

**Required Scopes:**
- `repo` (for private repositories)
- `read:packages` (if using GitHub Packages)

**Create Token:** Settings → Developer settings → Personal access tokens

```bash
export GIT_PM_TOKEN_github_com="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

---

#### GitLab

**Token Type:** Personal Access Token or Project Access Token

**Required Scopes:**
- `read_repository`

**Create Token:** User Settings → Access Tokens (or Project → Settings → Access Tokens)

```bash
export GIT_PM_TOKEN_gitlab_com="glpat-xxxxxxxxxxxxxxxxxxxx"
```

---

#### Bitbucket

**Token Type:** App Password (for Bitbucket Cloud) or HTTP Access Token (for Bitbucket Server)

**Required Permissions:**
- Repository: Read

**Create Token:** Personal settings → App passwords

```bash
# Bitbucket Cloud
export GIT_PM_TOKEN_bitbucket_org="your-app-password"

# Bitbucket Server (self-hosted)
export GIT_PM_TOKEN_bitbucket_mycompany_com="your-http-token"
```

---

#### Azure DevOps

**Option 1: Personal Access Token (AZURE_DEVOPS_PAT)**

**Required Scopes:**
- Code: Read

**Create Token:** User Settings → Personal Access Tokens

```bash
export AZURE_DEVOPS_PAT="your-pat-token"
```

**Option 2: System Access Token (SYSTEM_ACCESSTOKEN) - Recommended for Pipelines**

Available automatically in Azure Pipelines as `$(System.AccessToken)`.

```yaml
env:
  SYSTEM_ACCESSTOKEN: $(System.AccessToken)
```

**Required Pipeline Settings:**
- "Limit job authorization scope" may need adjustment for cross-project access
- Build Service account needs read access to target repositories

---

## ⚙️ Configuration Hierarchy

git-pm uses a 3-level configuration system with deep merging:

```
Defaults → User Config → Project Config → Environment Variables
```

Later sources override earlier ones. Environment variables have highest priority.

### Configuration Files

| Level | File | Scope |
|-------|------|-------|
| User | `~/.git-pm/config` | All projects for current user |
| Project | `git-pm.config` | Current project only |

### Configuration Keys

| Key | Type | Description | Default |
|-----|------|-------------|---------|
| `packages_dir` | string | Installation directory | `.git-packages` |
| `cache_dir` | string | Cache location | `~/.cache/git-pm` |
| `git_protocol` | object | Protocol per domain | `{}` |
| `url_patterns` | object | Custom URL templates | `{}` |
| `azure_devops_pat` | string | Azure DevOps PAT | `""` |

### Setting Configuration

**Via CLI:**
```bash
# Project-level
git-pm config packages_dir ".deps"
git-pm config git_protocol '{"dev.azure.com": "https"}'

# User-level (global)
git-pm config --global cache_dir "/tmp/git-pm-cache"
git-pm config --global git_protocol '{"github.com": "ssh", "dev.azure.com": "https"}'

# View all settings
git-pm config --list

# Unset a value
git-pm config --unset packages_dir
git-pm config --unset --global git_protocol
```

**Via JSON files:**

`~/.git-pm/config` (user-level):
```json
{
    "cache_dir": "/tmp/git-pm-cache",
    "git_protocol": {
        "github.com": "ssh",
        "gitlab.com": "ssh",
        "dev.azure.com": "https"
    }
}
```

`git-pm.config` (project-level):
```json
{
    "packages_dir": ".deps",
    "git_protocol": {
        "dev.azure.com": "https"
    }
}
```

### Protocol Selection

The `git_protocol` setting controls URL generation per domain:

| Value | Result |
|-------|--------|
| `ssh` | `git@{domain}:{path}.git` |
| `https` | `https://{domain}/{path}.git` |

**Note:** When authentication tokens are present, HTTPS is forced regardless of this setting.

---

## 🔄 Seamless Local & CI/CD Setup

### The Challenge

- **Local development:** SSH keys are available, SSH protocol preferred
- **CI/CD pipelines:** No SSH keys, must use HTTPS with tokens

### Solution: Protocol-Agnostic Repository References

Use shorthand repository references in `git-pm.json` that can be transformed to either protocol:

```json
{
    "packages": {
        "my-package": {
            "repo": "dev.azure.com/myorg/MyProject/my-repo",
            "path": "src/package",
            "ref": {
                "type": "tag",
                "value": "v1.0.0"
            }
        }
    }
}
```

git-pm automatically converts this to:
- **Local (SSH):** `git@ssh.dev.azure.com:v3/myorg/MyProject/my-repo`
- **CI/CD (HTTPS+token):** `https://{token}@dev.azure.com/myorg/MyProject/_git/my-repo`

### Supported Shorthand Formats

#### Azure DevOps
```
dev.azure.com/{org}/{project}/{repo}
dev.azure.com/{org}/{project}/_git/{repo}
```

#### GitHub
```
github.com/{owner}/{repo}
```

#### GitLab
```
gitlab.com/{owner}/{repo}
gitlab.mycompany.com/{group}/{subgroup}/{repo}
```

#### Bitbucket
```
bitbucket.org/{owner}/{repo}
```

### Local Development Setup

For local development with SSH:

1. **No configuration needed** - SSH is the default protocol
2. **Ensure SSH keys are configured** for your Git providers
3. **Run normally:**
   ```bash
   git-pm install
   ```

### CI/CD Pipeline Setup

For CI/CD pipelines:

1. **Set authentication environment variable:**
   ```bash
   export SYSTEM_ACCESSTOKEN="..."  # Azure DevOps
   # or
   export AZURE_DEVOPS_PAT="..."    # Azure DevOps
   # or
   export GIT_PM_TOKEN_github_com="..."  # GitHub
   ```

2. **Run normally:**
   ```bash
   git-pm install
   ```

The presence of authentication tokens automatically:
- Switches to HTTPS protocol
- Embeds or configures token authentication
- No manual protocol configuration needed

---

## 📁 Local Override Workflow

### Purpose

The `git-pm.local` file allows developers to override package sources for local development without modifying the committed `git-pm.json`.

### Use Cases

- Point to local filesystem copies of packages during development
- Use feature branches instead of tags
- Test changes before committing to shared packages

### How It Works

`git-pm.local` uses the same schema as `git-pm.json` and is merged at install time:

```
git-pm.json (base) + git-pm.local (override) = effective configuration
```

### Example

**git-pm.json** (committed):
```json
{
    "packages": {
        "shared-utils": {
            "repo": "dev.azure.com/myorg/Platform/shared-scripts",
            "path": "utils",
            "ref": {
                "type": "tag",
                "value": "v2.0.0"
            }
        }
    }
}
```

**git-pm.local** (not committed, in `.gitignore`):
```json
{
    "packages": {
        "shared-utils": {
            "repo": "file:///home/dev/projects/shared-scripts",
            "path": "utils"
        }
    }
}
```

**Result:** `shared-utils` is installed from local filesystem instead of remote repository.

### Override Rules

- Only specified fields are overridden
- Unspecified fields retain values from `git-pm.json`
- Can add new packages (only installed when `git-pm.local` is present)
- Cannot remove packages (only override them)

### Best Practices

1. **Always add to `.gitignore`:**
   ```gitignore
   git-pm.local
   ```

2. **Use absolute paths for file:// URLs:**
   ```json
   {"repo": "file:///absolute/path/to/repo"}
   ```

3. **Document expected overrides in README:**
   ```markdown
   ## Local Development
   
   Create `git-pm.local` to override package sources:
   ```json
   {
       "packages": {
           "shared-utils": {
               "repo": "file:///path/to/your/local/shared-scripts"
           }
       }
   }
   ```
   ```

---

## 🔧 CI/CD Pipeline Examples

### Azure DevOps Pipelines

#### Basic Setup (SYSTEM_ACCESSTOKEN - Recommended)

```yaml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
  - checkout: self
    persistCredentials: true

  - task: Bash@3
    displayName: 'Install git-pm'
    inputs:
      targetType: 'inline'
      script: |
        curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/install-git-pm.sh | bash

  - task: Bash@3
    displayName: 'Install packages'
    inputs:
      targetType: 'inline'
      script: |
        git-pm install
    env:
      SYSTEM_ACCESSTOKEN: $(System.AccessToken)
```

#### With Azure CLI Task

```yaml
trigger: none

pool:
  vmImage: 'ubuntu-latest'

variables:
  azureServiceConnection: 'my-azure-connection'

jobs:
  - job: Build
    steps:
      - task: AzureCLI@2
        displayName: 'Install dependencies'
        inputs:
          azureSubscription: $(azureServiceConnection)
          scriptType: 'bash'
          scriptLocation: 'inlineScript'
          inlineScript: |
            set -euo pipefail
            
            # Install git-pm
            curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/install-git-pm.sh | bash
            
            # Install packages
            git-pm install
            
            # Source environment and run scripts
            source .git-pm.env
            ./.git-packages/my-script/run.sh
        env:
          SYSTEM_ACCESSTOKEN: $(System.AccessToken)
```

#### Cross-Project Repository Access

When accessing repositories in different Azure DevOps projects:

1. **Adjust pipeline settings:**
   - Pipeline → Settings → "Limit job authorization scope to current project" → **Off**
   
2. **Grant permissions:**
   - Target repo → Security → Add `{Project} Build Service ({Org})` → **Read** access

```yaml
steps:
  - task: Bash@3
    displayName: 'Install cross-project packages'
    inputs:
      targetType: 'inline'
      script: |
        git-pm install
    env:
      SYSTEM_ACCESSTOKEN: $(System.AccessToken)
```

#### Using PAT Instead of System Token

For broader access or external triggers:

```yaml
variables:
  - group: 'git-credentials'  # Contains AZURE_DEVOPS_PAT

steps:
  - task: Bash@3
    displayName: 'Install packages'
    inputs:
      targetType: 'inline'
      script: |
        git-pm install
    env:
      AZURE_DEVOPS_PAT: $(AZURE_DEVOPS_PAT)
```

---

### GitHub Actions

#### Basic Setup

```yaml
name: Build

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install git-pm
        run: |
          curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/install-git-pm.sh | bash
      
      - name: Install packages
        run: git-pm install
        env:
          GIT_PM_TOKEN_github_com: ${{ secrets.GIT_PM_TOKEN }}
```

#### With Multiple Providers

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install git-pm
        run: |
          curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/install-git-pm.sh | bash
      
      - name: Install packages
        run: git-pm install
        env:
          GIT_PM_TOKEN_github_com: ${{ secrets.GITHUB_TOKEN }}
          GIT_PM_TOKEN_gitlab_com: ${{ secrets.GITLAB_TOKEN }}
          AZURE_DEVOPS_PAT: ${{ secrets.ADO_PAT }}
```

#### Using GitHub Token for Private Repos

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install packages
        run: |
          curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/install-git-pm.sh | bash
          git-pm install
        env:
          # GITHUB_TOKEN is automatically available
          GIT_PM_TOKEN_github_com: ${{ secrets.GITHUB_TOKEN }}
```

**Note:** `GITHUB_TOKEN` has read access to the current repository. For cross-repo access, create a PAT with appropriate scopes.

---

### GitLab CI

#### Basic Setup

```yaml
stages:
  - build

build:
  stage: build
  image: python:3.11
  
  before_script:
    - curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/install-git-pm.sh | bash
  
  script:
    - git-pm install
    - source .git-pm.env
    - ./run-build.sh
  
  variables:
    GIT_PM_TOKEN_gitlab_com: ${GITLAB_TOKEN}
```

#### Using CI Job Token

```yaml
build:
  stage: build
  image: python:3.11
  
  script:
    - curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/install-git-pm.sh | bash
    - git-pm install
  
  variables:
    # CI_JOB_TOKEN is automatically available
    GIT_PM_TOKEN_gitlab_com: ${CI_JOB_TOKEN}
```

**Note:** `CI_JOB_TOKEN` requires enabling "CI/CD job token access" in target project settings.

#### Multi-Provider Setup

```yaml
build:
  stage: build
  image: python:3.11
  
  script:
    - curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/install-git-pm.sh | bash
    - git-pm install
  
  variables:
    GIT_PM_TOKEN_gitlab_com: ${GITLAB_TOKEN}
    GIT_PM_TOKEN_github_com: ${GITHUB_TOKEN}
    AZURE_DEVOPS_PAT: ${ADO_PAT}
```

---

### Jenkins

#### Declarative Pipeline

```groovy
pipeline {
    agent any
    
    environment {
        GIT_PM_TOKEN_github_com = credentials('github-token')
        AZURE_DEVOPS_PAT = credentials('ado-pat')
    }
    
    stages {
        stage('Setup') {
            steps {
                sh '''
                    curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/install-git-pm.sh | bash
                '''
            }
        }
        
        stage('Install Dependencies') {
            steps {
                sh '''
                    export PATH="$HOME/.local/bin:$PATH"
                    git-pm install
                '''
            }
        }
        
        stage('Build') {
            steps {
                sh '''
                    source .git-pm.env
                    ./build.sh
                '''
            }
        }
    }
}
```

#### Scripted Pipeline

```groovy
node {
    stage('Checkout') {
        checkout scm
    }
    
    stage('Setup git-pm') {
        sh 'curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/install-git-pm.sh | bash'
    }
    
    stage('Install Dependencies') {
        withCredentials([
            string(credentialsId: 'github-token', variable: 'GIT_PM_TOKEN_github_com'),
            string(credentialsId: 'ado-pat', variable: 'AZURE_DEVOPS_PAT')
        ]) {
            sh '''
                export PATH="$HOME/.local/bin:$PATH"
                git-pm install
            '''
        }
    }
    
    stage('Build') {
        sh '''
            source .git-pm.env
            ./build.sh
        '''
    }
}
```

---

### Generic CI Template

For other CI systems, follow this pattern:

```bash
#!/bin/bash
set -euo pipefail

# 1. Set authentication (choose based on your provider)
export SYSTEM_ACCESSTOKEN="${SYSTEM_ACCESSTOKEN:-}"      # Azure DevOps
export AZURE_DEVOPS_PAT="${AZURE_DEVOPS_PAT:-}"          # Azure DevOps (alternative)
export GIT_PM_TOKEN_github_com="${GITHUB_TOKEN:-}"        # GitHub
export GIT_PM_TOKEN_gitlab_com="${GITLAB_TOKEN:-}"        # GitLab
export GIT_PM_TOKEN_bitbucket_org="${BITBUCKET_TOKEN:-}"  # Bitbucket

# 2. Install git-pm
curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/install-git-pm.sh | bash
export PATH="$HOME/.local/bin:$PATH"

# 3. Install packages
git-pm install

# 4. Source environment (optional, for scripts that need package paths)
source .git-pm.env

# 5. Run your build/deployment
./your-build-script.sh
```

---

## 🌐 Azure DevOps URL Formats

git-pm automatically handles multiple Azure DevOps URL formats:

### Supported Input Formats

| Format | Example |
|--------|---------|
| SSH | `git@ssh.dev.azure.com:v3/{org}/{project}/{repo}` |
| HTTPS with user | `https://{user}@dev.azure.com/{org}/{project}/_git/{repo}` |
| HTTPS | `https://dev.azure.com/{org}/{project}/_git/{repo}` |
| Shorthand with /_git/ | `dev.azure.com/{org}/{project}/_git/{repo}` |
| Shorthand | `dev.azure.com/{org}/{project}/{repo}` |
| Hybrid (legacy) | `dev.azure.com:v3/{org}/{project}/{repo}` |

### Automatic Transformation

All formats are normalized based on authentication:

**With SYSTEM_ACCESSTOKEN or AZURE_DEVOPS_PAT:**
```
https://[token@]dev.azure.com/{org}/{project}/_git/{repo}
```

**Without authentication (local SSH):**
```
git@ssh.dev.azure.com:v3/{org}/{project}/{repo}
```

### URL-Encoded Project Names

Projects with spaces are automatically handled:

```json
{
    "packages": {
        "my-pkg": {
            "repo": "dev.azure.com/myorg/Platform%20Engineering/shared-scripts"
        }
    }
}
```

Both `Platform%20Engineering` and `Platform Engineering` work correctly.

---

## 📝 Environment File

After `git-pm install`, a `.git-pm.env` file is generated:

```bash
# Generated by git-pm
GIT_PM_PACKAGES_DIR=/path/to/project/.git-packages
GIT_PM_PROJECT_ROOT=/path/to/project
```

### Usage in Scripts

```bash
#!/bin/bash
source .git-pm.env

# Reference installed packages
"${GIT_PM_PACKAGES_DIR}/my-script/run.sh"

# Or use relative paths
./.git-packages/my-script/run.sh
```

### Usage in Pipelines

```yaml
# Azure DevOps
- task: Bash@3
  inputs:
    targetType: 'inline'
    script: |
      source .git-pm.env
      "${GIT_PM_PACKAGES_DIR}/deploy/provision.sh"

# GitHub Actions
- name: Run deployment
  run: |
    source .git-pm.env
    "${GIT_PM_PACKAGES_DIR}/deploy/provision.sh"
```

---

## 🛡️ Security Best Practices

### Token Management

| ✅ Do | ❌ Don't |
|-------|---------|
| Use CI system's secret management | Hardcode tokens in pipelines |
| Use `SYSTEM_ACCESSTOKEN` for Azure DevOps | Commit tokens to repositories |
| Rotate tokens regularly | Share tokens across projects |
| Use minimum required scopes | Use admin/write tokens for read-only operations |
| Use `git-pm.local` for local overrides | Commit local development paths |

### Recommended Token Scopes

| Provider | Scope | Permission |
|----------|-------|------------|
| Azure DevOps | Code | Read |
| GitHub | repo (private) / public_repo | Read |
| GitLab | read_repository | Read |
| Bitbucket | Repository | Read |

### Masking Tokens in Logs

- **Azure DevOps:** Tokens in `$(...)` syntax are automatically masked
- **GitHub Actions:** Secrets are automatically masked
- **GitLab CI:** Variables marked as "masked" are hidden
- **Jenkins:** Use `credentials()` binding for masking

**git-pm behavior:**
- `SYSTEM_ACCESSTOKEN`: Never appears in URLs or logs ✅
- `AZURE_DEVOPS_PAT`: Appears in git URLs (masked by CI system)
- `GIT_PM_TOKEN_*`: Appears in git URLs (masked by CI system)

---

## 🐛 Troubleshooting

### Authentication Errors

#### "Repository not found" or "Authentication failed"

**Causes:**
1. Token not set or expired
2. Insufficient permissions
3. Wrong URL format

**Solutions:**

```bash
# Verify token is set
echo "Token set: ${SYSTEM_ACCESSTOKEN:+yes}"
echo "PAT set: ${AZURE_DEVOPS_PAT:+yes}"

# Test authentication manually
git ls-remote https://dev.azure.com/{org}/{project}/_git/{repo}

# Check Azure DevOps permissions
# Go to: Project Settings → Repositories → Security
# Ensure Build Service has "Read" access
```

#### "TF401019: The Git repository... does not exist"

**Cause:** Incorrect URL format (usually missing `/_git/` segment)

**Solution:** Use shorthand format in `git-pm.json`:
```json
{
    "repo": "dev.azure.com/{org}/{project}/{repo}"
}
```
git-pm will automatically add `/_git/` when needed.

#### "Port number was not a decimal number"

**Cause:** Malformed URL like `dev.azure.com:v3/...`

**Solution:** This format is now supported, but prefer:
```json
{
    "repo": "dev.azure.com/{org}/{project}/{repo}"
}
```

### Pipeline-Specific Issues

#### Azure DevOps: Cross-Project Access Denied

**Cause:** Job authorization scope limited to current project

**Solution:**
1. Pipeline → Edit → Triggers → YAML → Get Sources
2. Disable "Limit job authorization scope to current project for non-release pipelines"

Or use a PAT with cross-project access:
```yaml
env:
  AZURE_DEVOPS_PAT: $(CROSS_PROJECT_PAT)
```

#### GitHub Actions: Private Repo Access

**Cause:** `GITHUB_TOKEN` only has access to current repository

**Solution:** Create a PAT with `repo` scope:
```yaml
env:
  GIT_PM_TOKEN_github_com: ${{ secrets.PRIVATE_REPO_PAT }}
```

#### GitLab CI: CI_JOB_TOKEN Access Denied

**Cause:** Job token access not enabled in target project

**Solution:**
1. Target project → Settings → CI/CD → Token Access
2. Add your project to "Allow CI job tokens from the following projects"

Or use a personal access token:
```yaml
variables:
  GIT_PM_TOKEN_gitlab_com: ${GITLAB_PAT}
```

### Cache Issues

#### Stale packages after update

**Cause:** Cached version doesn't match new tag

**Solution:**
```bash
# Clear cache
rm -rf ~/.cache/git-pm

# Or clean and reinstall
git-pm clean
git-pm install
```

#### In CI/CD (cache between runs):
```yaml
# Azure DevOps - no cache by default, fresh each run

# GitHub Actions - clear cache if needed
- name: Clear git-pm cache
  run: rm -rf ~/.cache/git-pm
```

---

## 📊 Quick Reference

### Environment Variables

| Variable | Provider | URL Embedding | Priority |
|----------|----------|---------------|----------|
| `AZURE_DEVOPS_PAT` | Azure DevOps | Yes | 1 |
| `SYSTEM_ACCESSTOKEN` | Azure DevOps | No (http.extraheader) | 2 |
| `GIT_PM_TOKEN_github_com` | GitHub | Yes | 3 |
| `GIT_PM_TOKEN_gitlab_com` | GitLab | Yes (oauth2:) | 3 |
| `GIT_PM_TOKEN_bitbucket_org` | Bitbucket | Yes (oauth2:) | 3 |
| `GIT_PM_TOKEN_{domain}` | Any | Yes (oauth2:) | 3 |

### Configuration Files

| File | Location | Committed | Purpose |
|------|----------|-----------|---------|
| `git-pm.json` | Project root | ✅ Yes | Package manifest |
| `git-pm.config` | Project root | ✅ Yes | Project configuration |
| `git-pm.local` | Project root | ❌ No | Local overrides |
| `~/.git-pm/config` | Home directory | N/A | User configuration |
| `.git-pm.env` | Project root | ❌ No | Generated environment |

### Generated Files (.gitignore)

```gitignore
# git-pm
.git-packages/
.git-pm.env
git-pm.local
```

### Commands

| Command | Purpose |
|---------|---------|
| `git-pm install` | Install all packages |
| `git-pm clean` | Remove installed packages |
| `git-pm config --list` | Show all configuration |
| `git-pm config <key>` | Get configuration value |
| `git-pm config <key> <value>` | Set project configuration |
| `git-pm config --global <key> <value>` | Set user configuration |

---

## 📚 Additional Resources

- [git-pm Repository](https://github.com/Warrenn/git-pm)
- [Azure DevOps Pipeline YAML Reference](https://docs.microsoft.com/en-us/azure/devops/pipelines/yaml-schema)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitLab CI/CD Documentation](https://docs.gitlab.com/ee/ci/)
- [Jenkins Pipeline Syntax](https://www.jenkins.io/doc/book/pipeline/syntax/)

---

## 📝 Summary

| Scenario | Recommended Setup |
|----------|-------------------|
| Azure DevOps Pipeline | `SYSTEM_ACCESSTOKEN: $(System.AccessToken)` |
| GitHub Actions (private repos) | `GIT_PM_TOKEN_github_com: ${{ secrets.PAT }}` |
| GitLab CI (same group) | `GIT_PM_TOKEN_gitlab_com: ${CI_JOB_TOKEN}` |
| Multi-provider | Set multiple `GIT_PM_TOKEN_*` variables |
| Local development | No config needed (SSH auto-detected) |
| Local testing with HTTPS | `git-pm.local` with `file://` URLs |

**Key Principles:**
1. ✅ Use shorthand repo URLs in `git-pm.json` for portability
2. ✅ Let environment variables control authentication
3. ✅ Use `SYSTEM_ACCESSTOKEN` for Azure DevOps pipelines
4. ✅ Use `git-pm.local` for local development overrides
5. ✅ Never commit tokens or local paths to repositories