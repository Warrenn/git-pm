# Quick Release Guide

## Create a Release in 3 Steps

### Step 1: Commit Your Changes

```bash
git add .
git commit -m "Your commit message"
git push origin main
```

### Step 2: Create and Push a Tag

```bash
# Create a version tag (e.g., v0.0.1, v0.1.0, v1.0.0)
git tag -a v0.0.1 -m "Release version 0.0.1"

# Push the tag to GitHub
git push origin v0.0.1
```

### Step 3: Wait for GitHub Actions

The workflow will automatically:
- ✅ Create a tar.gz archive
- ✅ Generate SHA256 checksum
- ✅ Create a GitHub Release
- ✅ Upload files and release notes

**Done!** Your release will be available at:
```
https://github.com/YOUR_USERNAME/YOUR_REPO/releases
```

## Tag Format

Use semantic versioning with a `v` prefix:

- `v0.0.1` - Initial release
- `v0.1.0` - Minor update
- `v1.0.0` - Major release
- `v1.2.3` - Patch release

## What Gets Included in the Tar File

✅ Included:
- `git-pm.py`
- All documentation (*.md files)
- `examples/` directory
- Test scripts (`*.sh`)

❌ Excluded:
- `.git/` directory
- `.github/` workflows
- `test-workspace/` 
- `simple-test/` artifacts
- `__pycache__/` and `*.pyc`

## Verify Your Release

After pushing the tag:

1. Check workflow status:
   ```
   https://github.com/YOUR_USERNAME/YOUR_REPO/actions
   ```

2. View your release:
   ```
   https://github.com/YOUR_USERNAME/YOUR_REPO/releases
   ```

3. Download and test:
   ```bash
   # One-liner: Download, extract to git-pm folder, and cleanup
   curl -L -o git-pm-0.0.1.tar.gz https://github.com/YOUR_USERNAME/YOUR_REPO/releases/download/v0.0.1/git-pm-0.0.1.tar.gz && mkdir -p git-pm && tar -xzf git-pm-0.0.1.tar.gz -C git-pm --strip-components=1 && rm git-pm-0.0.1.tar.gz
   
   # Or step-by-step:
   wget https://github.com/YOUR_USERNAME/YOUR_REPO/releases/download/v0.0.1/git-pm-0.0.1.tar.gz
   tar -xzf git-pm-0.0.1.tar.gz
   cd git-pm
   python git-pm.py --version
   ```

## User Installation Instructions

Share this with users who want to install your tool:

```bash
# Install git-pm v0.0.1
curl -L -o git-pm.tar.gz https://github.com/YOUR_USERNAME/YOUR_REPO/releases/download/v0.0.1/git-pm-0.0.1.tar.gz && mkdir -p git-pm && tar -xzf git-pm.tar.gz -C git-pm --strip-components=1 && rm git-pm.tar.gz

# Verify installation
cd git-pm
python git-pm.py --version
```

Replace `v0.0.1`, `0.0.1`, and `YOUR_USERNAME/YOUR_REPO` with actual values.

## Troubleshooting

### Workflow didn't trigger?
- Check tag matches pattern: `v*.*.*` (with lowercase 'v')
- Verify Actions are enabled in repository settings
- Check the Actions tab for errors

### Need to delete a tag?
```bash
# Delete local tag
git tag -d v0.0.1

# Delete remote tag
git push origin :refs/tags/v0.0.1
```

### Want to re-release?
1. Delete the tag (see above)
2. Delete the release on GitHub
3. Create the tag again

## Complete Example

```bash
# Make changes
vim git-pm.py

# Test everything works
./test-git-pm.sh all

# Commit
git add .
git commit -m "Add new feature"
git push origin main

# Create and push tag
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0

# Wait 1-2 minutes for GitHub Actions
# Check: https://github.com/YOUR_USERNAME/YOUR_REPO/releases
```

That's it! 🚀
