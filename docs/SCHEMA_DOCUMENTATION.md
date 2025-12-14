# git-pm JSON Schema Documentation

## Overview

JSON schemas provide IDE autocomplete, validation, and documentation for git-pm configuration files. This guide shows how to configure your IDE to use git-pm schemas.

---

## Schema Files

Three JSON schema files are provided:

| File | Schema | Purpose |
|------|--------|---------|
| `git-pm.json` | `git-pm.schema.json` | Package manifest (committed) |
| `git-pm.local` | `git-pm.local.schema.json` | Local overrides (not committed) |
| `git-pm.config` | `git-pm.config.schema.json` | Configuration (project/user level) |

**GitHub Raw URLs:**
```
https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.schema.json
https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.local.schema.json
https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.config.schema.json
```

---

## Method 1: Inline $schema (Recommended - Universal)

Add a `$schema` property to the top of each file. **This works in all modern IDEs** (VS Code, JetBrains, Visual Studio, etc.).

### git-pm.json
```json
{
  "$schema": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.schema.json",
  "packages": {
    "my-package": {
      "repo": "github:owner/repo",
      "path": "",
      "ref": {
        "type": "tag",
        "value": "v1.0.0"
      }
    }
  }
}
```

### git-pm.local
```json
{
  "$schema": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.local.schema.json",
  "packages": {
    "my-package": {
      "repo": "file:///home/user/dev/package",
      "path": "",
      "ref": {
        "type": "branch",
        "value": "main"
      }
    }
  }
}
```

### git-pm.config
```json
{
  "$schema": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.config.schema.json",
  "packages_dir": ".git-packages",
  "cache_dir": "~/.cache/git-pm"
}
```

**Benefits:**
- ✅ Works universally across all IDEs
- ✅ No IDE-specific configuration needed
- ✅ Portable - schemas travel with files
- ✅ Team members get schemas automatically

**Drawbacks:**
- Schema URL visible in file
- Must be added to each file

---

## Method 2: VS Code Settings (File Association)

Configure VS Code to automatically associate file patterns with schemas.

### Option A: Workspace Settings (Recommended)

Create or edit `.vscode/settings.json` in your project:

```json
{
  "json.schemas": [
    {
      "fileMatch": ["git-pm.json"],
      "url": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.schema.json"
    },
    {
      "fileMatch": ["git-pm.local"],
      "url": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.local.schema.json"
    },
    {
      "fileMatch": ["git-pm.config", ".git-pm/config"],
      "url": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.config.schema.json"
    }
  ]
}
```

**Benefits:**
- ✅ Automatic for all team members who open the workspace
- ✅ No modification to config files
- ✅ Centralized configuration

**Drawbacks:**
- Only works for VS Code
- Requires workspace setup

### Option B: User Settings (Global)

Open VS Code Settings (Cmd/Ctrl + ,) → Search "json.schemas" → Edit in settings.json:

```json
{
  "json.schemas": [
    {
      "fileMatch": ["**/git-pm.json"],
      "url": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.schema.json"
    },
    {
      "fileMatch": ["**/git-pm.local"],
      "url": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.local.schema.json"
    },
    {
      "fileMatch": ["**/git-pm.config", "**/.git-pm/config"],
      "url": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.config.schema.json"
    }
  ]
}
```

**Benefits:**
- ✅ Applies to all your projects
- ✅ Set once, works everywhere

**Drawbacks:**
- Only affects your machine
- Team members must configure separately

---

## Method 3: Local Schema Files

If you prefer not to use GitHub URLs, you can reference local schema files.

### Directory Structure
```
your-project/
├── .vscode/
│   └── settings.json
├── schemas/
│   ├── git-pm.schema.json
│   ├── git-pm.local.schema.json
│   └── git-pm.config.schema.json
├── git-pm.json
├── git-pm.local
└── git-pm.config
```

### .vscode/settings.json
```json
{
  "json.schemas": [
    {
      "fileMatch": ["git-pm.json"],
      "url": "./schemas/git-pm.schema.json"
    },
    {
      "fileMatch": ["git-pm.local"],
      "url": "./schemas/git-pm.local.schema.json"
    },
    {
      "fileMatch": ["git-pm.config"],
      "url": "./schemas/git-pm.config.schema.json"
    }
  ]
}
```

**Benefits:**
- ✅ Works offline
- ✅ Faster (no network request)
- ✅ Version controlled with project

**Drawbacks:**
- Schemas must be kept up to date manually
- Larger repository size

---

## Other IDEs

### JetBrains IDEs (IntelliJ, WebStorm, PyCharm, etc.)

**Method 1: Inline $schema (Recommended)**

Just add `$schema` to your JSON files as shown in Method 1.

**Method 2: Settings**

1. Go to: **Settings** → **Languages & Frameworks** → **Schemas and DTDs** → **JSON Schema Mappings**
2. Click **+** to add new mapping
3. Configure:
   - **Name:** `git-pm Manifest`
   - **Schema URL:** `https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.schema.json`
   - **File path pattern:** `git-pm.json`
4. Repeat for `git-pm.local` and `git-pm.config`

### Visual Studio

**Method 1: Inline $schema (Recommended)**

Add `$schema` property to JSON files.

**Method 2: JSON Schema Store**

Visual Studio uses the [JSON Schema Store](https://schemastore.org/). To add git-pm schemas globally:

1. Submit PR to https://github.com/SchemaStore/schemastore
2. Add schemas to catalog
3. Visual Studio will auto-detect

### Sublime Text

Install **LSP-json** package, then use inline `$schema` property.

### Vim/Neovim

Install **coc-json** (for coc.nvim) or **nvim-lspconfig** with **jsonls**, then use inline `$schema`.

---

## Publishing Schemas to GitHub

### Step 1: Add Schemas to Repository

```bash
# Create schemas directory
mkdir -p schemas

# Copy schema files
cp git-pm.schema.json schemas/
cp git-pm.local.schema.json schemas/
cp git-pm.config.schema.json schemas/

# Commit
git add schemas/
git commit -m "Add JSON schemas for IDE support"
git push origin main
```

### Step 2: Update $id in Schemas

Edit each schema file and replace `Warrenn` with your actual GitHub username:

```json
{
  "$id": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.schema.json",
  ...
}
```

### Step 3: Get Raw URLs

Your schemas are now available at:
```
https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.schema.json
https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.local.schema.json
https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.config.schema.json
```

### Step 4: Test

Create a test file with `$schema`:
```json
{
  "$schema": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.schema.json",
  "packages": {}
}
```

Open in VS Code - you should see:
- ✅ Autocomplete for properties
- ✅ Validation errors for invalid values
- ✅ Hover documentation

---

## Schema Features

### Autocomplete

Type `"` inside the packages object and you'll see:
- `repo` - Repository URL
- `path` - Path within repo
- `ref` - Git reference

### Validation

Invalid values are highlighted:
```json
{
  "packages": {
    "my-pkg": {
      "ref": {
        "type": "invalid"  // ❌ Error: must be tag, branch, or commit
      }
    }
  }
}
```

### Documentation on Hover

Hover over any property to see its description and examples.

### Required Fields

Missing required fields are highlighted:
```json
{
  "packages": {
    "my-pkg": {
      "repo": "github:org/repo"
      // ❌ Missing required fields: path, ref
    }
  }
}
```

---

## Advanced Configuration

### Custom Schema Server

Host schemas on your own server:

```json
{
  "$schema": "https://schemas.yourcompany.com/git-pm/manifest.schema.json",
  "packages": {}
}
```

### Schema Caching

VS Code caches schemas. To refresh:
1. Command Palette (Cmd/Ctrl + Shift + P)
2. Type: "Reload Window"

Or manually clear cache:
```bash
# macOS/Linux
rm -rf ~/.vscode/extensions/ms-vscode.vscode-json-*

# Windows
rmdir /s %USERPROFILE%\.vscode\extensions\ms-vscode.vscode-json-*
```

### Private Repositories

For private GitHub repos, VS Code may require authentication. Use a local schema file instead or set up authentication.

---

## Recommended Setup

### For Teams

**Use workspace settings with inline $schema as fallback:**

1. Add `.vscode/settings.json` with schema mappings
2. Add `$schema` to template files in documentation
3. Commit schemas to repository
4. Document in README

### For Personal Projects

**Use inline $schema:**

Simply add `$schema` property to each file. No configuration needed.

---

## Example Files with Schemas

### Complete git-pm.json

```json
{
  "$schema": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.schema.json",
  "packages": {
    "ui-components": {
      "repo": "github:myorg/ui-library",
      "path": "packages/components",
      "ref": {
        "type": "tag",
        "value": "v2.1.0"
      }
    },
    "utils": {
      "repo": "https://github.com/myorg/utils.git",
      "path": "",
      "ref": {
        "type": "branch",
        "value": "main"
      }
    }
  }
}
```

### Complete git-pm.local

```json
{
  "$schema": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.local.schema.json",
  "packages": {
    "ui-components": {
      "repo": "file:///Users/dev/projects/ui-library",
      "path": "packages/components",
      "ref": {
        "type": "branch",
        "value": "feature-new-button"
      }
    }
  }
}
```

### Complete git-pm.config

```json
{
  "$schema": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.config.schema.json",
  "packages_dir": ".deps",
  "cache_dir": "~/.cache/git-pm",
  "git_protocol": {},
  "url_patterns": {}
}
```

---

## Troubleshooting

### Schema Not Working in VS Code

1. **Check file name matches pattern**
   - Must be exactly `git-pm.json`, `git-pm.local`, or `git-pm.config`

2. **Reload window**
   - Cmd/Ctrl + Shift + P → "Reload Window"

3. **Check schema URL is accessible**
   - Open URL in browser, should show JSON

4. **Verify JSON is valid**
   - Look for syntax errors (trailing commas, etc.)

### Schema Not Updating

1. **Clear VS Code cache**
   ```bash
   rm -rf ~/.vscode/extensions/ms-vscode.vscode-json-*
   ```

2. **Use Cmd/Ctrl + Shift + P → "Reload Window"**

3. **Hard-code a version in URL**
   ```
   https://raw.githubusercontent.com/user/git-pm/v1.0.0/schemas/git-pm.schema.json
   ```

### Autocomplete Not Showing

1. **Ensure you're inside the right context**
   - Autocomplete shows based on cursor position

2. **Trigger manually**
   - Press Ctrl + Space

3. **Check VS Code JSON extension is enabled**

---

## Summary

### Quick Start

**Easiest method (works everywhere):**

Add to top of each file:
```json
{
  "$schema": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/SCHEMA-NAME.schema.json",
  ...
}
```

**For teams (VS Code):**

Add `.vscode/settings.json`:
```json
{
  "json.schemas": [
    {
      "fileMatch": ["git-pm.json"],
      "url": "https://raw.githubusercontent.com/Warrenn/git-pm/main/schemas/git-pm.schema.json"
    }
  ]
}
```

---

## Benefits

✅ **Autocomplete** - Type-ahead for all properties  
✅ **Validation** - Real-time error detection  
✅ **Documentation** - Inline help on hover  
✅ **Type safety** - Prevent configuration errors  
✅ **Team consistency** - Everyone uses same schema  
✅ **Universal** - Works across IDEs  

Happy coding with git-pm! 🚀
