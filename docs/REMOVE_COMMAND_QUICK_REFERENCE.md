# Remove Command - Quick Reference

## Syntax

```bash
git-pm remove <package-name> [-y]
```

## Examples

### Remove with confirmation
```bash
git-pm remove my-package
```

### Remove without confirmation
```bash
git-pm remove my-package -y
```

## What It Does

1. **Removes from manifests:**
   - ✓ git-pm.json (if present)
   - ✓ git-pm.local (if present)

2. **Removes from disk:**
   - ✓ `.git-packages/<package-name>/`
   - ✓ Dependencies (if not needed by others)

3. **Updates:**
   - ✓ `.git-pm.env` (removes package entries)

4. **Preserves:**
   - ✓ Cache (`~/.cache/git-pm/`)
   - ✓ Packages needed by others

## Behavior

### Dependency Cascade

```
project
├── pkg-a (remove this)
│   └── pkg-b (auto-removed)
│       └── pkg-d (kept - also needed by pkg-x)
└── pkg-x (kept)
    └── pkg-d (kept)
```

**Result:** Removes pkg-a and pkg-b, keeps pkg-d and pkg-x

### Deep Recursion

The command analyzes dependencies at **any depth**:
- Follows entire dependency chain
- Only removes if no package needs it
- Never breaks dependencies

## Common Scenarios

### Scenario 1: Remove Unused Package
```bash
# Package not needed by anything
git-pm remove old-package -y

Result:
✓ Removed from manifest
✓ Removed from disk
```

### Scenario 2: Remove Package with Dependencies
```bash
# Package has 2 dependencies
git-pm remove parent-package -y

Result:
✓ parent-package removed
✓ child-1 removed (no longer needed)
✓ child-2 removed (no longer needed)
```

### Scenario 3: Remove Shared Dependency
```bash
# Package used by others
git-pm remove shared-package -y

Result:
✓ Removed from manifest
✗ Kept on disk (still needed by other packages)
```

## Flags

| Flag | Effect |
|------|--------|
| `-y, --yes` | Skip confirmation |
| `-h, --help` | Show help |

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Package not found or error |

## Safety Features

✅ **Never breaks dependencies**  
✅ **Shows preview before removing**  
✅ **Requires confirmation** (unless -y)  
✅ **Preserves packages in use**  
✅ **No --force flag** (intentional)  

## Troubleshooting

### "Package not found"
→ Check spelling and manifest files

### Package still on disk after removal
→ Other packages need it (expected behavior)

### Want to remove everything
→ Use `git-pm clean` instead

## Integration

```bash
# Remove and reinstall
git-pm remove pkg
git-pm add pkg github.com/org/repo --ref-type tag --ref-value v2.0.0
git-pm install

# Remove multiple (one at a time)
git-pm remove pkg-a -y
git-pm remove pkg-b -y
```

## See Also

- `git-pm clean` - Remove all packages
- `git-pm install` - Install packages
- `git-pm add` - Add to manifest

## Full Documentation

See **REMOVE_COMMAND_DOCUMENTATION.md** for:
- Detailed examples
- Algorithm explanation
- Edge cases
- Best practices
