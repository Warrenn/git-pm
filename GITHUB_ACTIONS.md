# GitHub Actions Guide

This document explains how to use the GitHub Actions workflows included with git-pm.

## Workflows Included

### 1. Release Workflow (`release.yml`)
**Full-featured release automation**

- **Triggers**: When you push a version tag (e.g., `v0.0.1`, `v1.2.3`)
- **What it does**:
  - Creates a tar.gz archive of the repository
  - Generates release notes automatically
  - Creates a GitHub Release
  - Uploads the tar.gz file as a release asset
  - Saves artifact for debugging

### 2. Simple Release Workflow (`release-simple.yml`)
**Minimal release automation**

- **Triggers**: When you push a version tag
- **What it does**:
  - Creates a tar.gz archive
  - Creates a GitHub Release with the archive

### 3. CI Tests Workflow (`ci.yml`)
**Continuous integration testing**

- **Triggers**: On push to main/develop branches, or pull requests
- **What it does**:
  - Tests on Python 3.6 through 3.11
  - Runs simple test
  - Runs comprehensive test suite
  - Validates Python syntax
  - Checks documentation files exist
  - Validates YAML examples

## How to Create a Release

### Method 1: Using Git Tags (Recommended)

1. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Release version 0.0.1"
   ```

2. **Create and push a version tag**:
   ```bash
   # Create annotated tag
   git tag -a v0.0.1 -m "Release version 0.0.1"
   
   # Push the tag to GitHub
   git push origin v0.0.1
   ```

3. **GitHub Actions will automatically**:
   - Detect the tag push
   - Run the release workflow
   - Create a tar.gz file
   - Create a GitHub Release
   - Attach the tar.gz to the release

4. **View your release**:
   - Go to: `https://github.com/YOUR-USERNAME/YOUR-REPO/releases`
   - You'll see your new release with the downloadable tar.gz file

### Method 2: Using GitHub CLI

```bash
# Commit changes
git add .
git commit -m "Release version 0.0.1"

# Create tag and push
git tag v0.0.1
git push origin v0.0.1

# The workflow runs automatically
# Check status:
gh run list
```

### Method 3: Using GitHub Web Interface

1. Go to your repository on GitHub
2. Click "Releases" → "Draft a new release"
3. Click "Choose a tag"
4. Type a new tag: `v0.0.1`
5. Click "Create new tag: v0.0.1 on publish"
6. Fill in release details
7. Click "Publish release"
8. The workflow will trigger and add the tar.gz file

## Version Numbering

The workflows expect tags in the format: `v<major>.<minor>.<patch>`

### Valid Examples:
- ✅ `v0.0.1`
- ✅ `v1.0.0`
- ✅ `v2.3.15`
- ✅ `v10.5.2`

### Invalid Examples:
- ❌ `0.0.1` (missing 'v' prefix)
- ❌ `v1.0` (missing patch number)
- ❌ `release-1.0.0` (wrong format)
- ❌ `v1.0.0-beta` (will not trigger - modify workflow pattern if needed)

## Customizing Workflows

### To Support Pre-release Tags

Edit `.github/workflows/release.yml`:

```yaml
on:
  push:
    tags:
      - 'v*.*.*'           # Normal releases
      - 'v*.*.*-alpha*'    # Alpha releases
      - 'v*.*.*-beta*'     # Beta releases
      - 'v*.*.*-rc*'       # Release candidates
```

### To Exclude Files from Archive

Edit the `tar` command in the workflow:

```yaml
- name: Create tar archive
  run: |
    tar -czf "git-pm-$VERSION.tar.gz" \
      --exclude='.git' \
      --exclude='.github' \
      --exclude='test-workspace' \
      --exclude='simple-test' \
      --exclude='YOUR-FILE-HERE' \
      .
```

### To Change Python Versions Tested

Edit `.github/workflows/ci.yml`:

```yaml
strategy:
  matrix:
    python-version: ['3.8', '3.9', '3.10', '3.11', '3.12']
```

## Choosing Between Release Workflows

### Use `release.yml` (Full) if you want:
- ✅ Automatic release notes generation
- ✅ Formatted release description
- ✅ Version extraction from tag
- ✅ Debug artifacts saved
- ✅ More control over release process

### Use `release-simple.yml` (Simple) if you want:
- ✅ Minimal configuration
- ✅ Just tar and release
- ✅ Manual release notes (write them yourself)
- ✅ Faster execution

**Recommendation**: Use `release.yml` for most cases. It's better documented and provides more features.

## Workflow File Locations

```
.github/
└── workflows/
    ├── release.yml          # Full release workflow (USE THIS)
    ├── release-simple.yml   # Simple alternative
    └── ci.yml               # CI testing
```

## Setting Up in Your Repository

### 1. Copy Files to Your Repository

```bash
# In your repository root
mkdir -p .github/workflows
cp path/to/release.yml .github/workflows/
cp path/to/ci.yml .github/workflows/

# Commit
git add .github/
git commit -m "Add GitHub Actions workflows"
git push
```

### 2. Verify Workflows are Enabled

1. Go to your GitHub repository
2. Click "Actions" tab
3. You should see: "CI Tests" and "Create Release"
4. If you see a message about workflows, click "I understand my workflows, go ahead and enable them"

### 3. Test the CI Workflow

```bash
# Make a change
echo "# Test" >> README.md
git add README.md
git commit -m "Test CI"
git push

# Watch the CI workflow run
# Go to: GitHub → Your Repo → Actions
```

### 4. Create Your First Release

```bash
# Create and push a tag
git tag -a v0.0.1 -m "First release"
git push origin v0.0.1

# Watch the release workflow run
# Go to: GitHub → Your Repo → Actions
# Then check: GitHub → Your Repo → Releases
```

## Troubleshooting

### Workflow Doesn't Trigger

**Check:**
1. Tag format is correct: `v*.*.*`
2. Tag was pushed: `git push origin v0.0.1`
3. Workflows are enabled in repository settings
4. `.github/workflows/` directory exists in repository

### Release Creation Fails

**Common causes:**
1. `GITHUB_TOKEN` permissions insufficient
   - Solution: Workflows have `permissions: contents: write` set
2. Release already exists for this tag
   - Solution: Delete the existing release or use a new tag
3. Tar creation fails
   - Solution: Check the exclude patterns in workflow

### Tests Fail in CI

**Check:**
1. Python version compatibility
2. Git is installed in the runner (it should be by default)
3. Test scripts have execute permissions
4. All test dependencies are available

### How to View Workflow Logs

1. Go to repository on GitHub
2. Click "Actions" tab
3. Click on a workflow run
4. Click on a job (e.g., "create-release")
5. Expand steps to see detailed logs

## Example Release Process

Here's a complete example of releasing version 0.1.0:

```bash
# 1. Make sure you're on main branch and up to date
git checkout main
git pull

# 2. Update version in your code (if applicable)
# Edit git-pm.py and change __version__ = "0.1.0"
# Or update documentation with new version

# 3. Commit any changes
git add .
git commit -m "Prepare release 0.1.0"
git push

# 4. Create and push the tag
git tag -a v0.1.0 -m "Release version 0.1.0

## Changes in this release
- Feature: Added new command
- Fix: Fixed bug in parsing
- Docs: Updated documentation
"

git push origin v0.1.0

# 5. Wait for GitHub Actions to complete
# Visit: https://github.com/YOUR-USERNAME/YOUR-REPO/actions

# 6. Check the release
# Visit: https://github.com/YOUR-USERNAME/YOUR-REPO/releases

# 7. Download and test the release archive
# One-liner:
curl -L -o git-pm.tar.gz https://github.com/YOUR-USERNAME/YOUR-REPO/releases/download/v0.1.0/git-pm-0.1.0.tar.gz && mkdir -p git-pm && tar -xzf git-pm.tar.gz -C git-pm --strip-components=1 && rm git-pm.tar.gz
cd git-pm
./simple-test.sh

# Or step-by-step:
# wget https://github.com/YOUR-USERNAME/YOUR-REPO/releases/download/v0.1.0/git-pm-0.1.0.tar.gz
# tar -xzf git-pm-0.1.0.tar.gz
# cd git-pm-0.1.0
# ./simple-test.sh
```

## Security Considerations

### GitHub Token
- The `GITHUB_TOKEN` is automatically provided by GitHub Actions
- It's scoped to the repository
- It expires after the workflow completes
- No secrets need to be configured

### Permissions
The workflows use:
```yaml
permissions:
  contents: write  # Required to create releases
```

This is the minimum permission needed for releases.

### Private Repositories
These workflows work the same way in private repositories.

## Advanced: Manual Release (Without Workflow)

If you want to create releases manually:

```bash
# 1. Create tar file
VERSION="0.0.1"
tar -czf "git-pm-${VERSION}.tar.gz" \
  --exclude='.git' \
  --exclude='.github' \
  --exclude='test-workspace' \
  .

# 2. Create release with GitHub CLI
gh release create "v${VERSION}" \
  "git-pm-${VERSION}.tar.gz" \
  --title "Release v${VERSION}" \
  --notes "Release notes here"

# Or upload to existing release
gh release upload "v${VERSION}" "git-pm-${VERSION}.tar.gz"
```

## Continuous Delivery vs Continuous Deployment

Currently configured as **Continuous Delivery**:
- Releases are triggered by tags
- You control when releases happen
- Tests run on all commits

For **Continuous Deployment** (automatic release on main branch):
- Would need to modify workflow to trigger on push to main
- Would need to determine version automatically
- Not recommended for this project

## FAQ

**Q: Can I delete a release?**
A: Yes, go to Releases → Click release → Delete release

**Q: Can I edit release notes after publishing?**
A: Yes, go to Releases → Click release → Edit release

**Q: What if the tag already exists?**
A: Delete it first: `git tag -d v0.0.1 && git push origin :refs/tags/v0.0.1`

**Q: How do I make a pre-release?**
A: Edit the workflow to set `prerelease: true` or mark it in the GitHub UI

**Q: Can I trigger the workflow manually?**
A: Add `workflow_dispatch:` to the `on:` section to enable manual triggers

**Q: Do I need to create the .github directory?**
A: Yes, create `.github/workflows/` and put workflow files there

## Next Steps

1. Copy workflows to your repository
2. Commit and push
3. Create your first release tag
4. Check Actions tab to see it run
5. Download and test the release artifact

For more information on GitHub Actions, see:
https://docs.github.com/en/actions
