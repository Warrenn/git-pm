# Windows Symlink Support - Quick Guide

## 🎯 Yes, Symlinks Work on Windows!

git-pm now includes **automatic Windows support** with intelligent fallback:

## ✅ Three Automatic Scenarios

### Scenario 1: Developer Mode Enabled (Best)

**Output:**
```bash
🔗 Creating dependency symlinks...
  ✓ azure_bootstrap/aws_account -> aws_account
  ✓ azure_bootstrap/aws_ou -> aws_ou
```

**Creates:** True symlinks (like Linux/macOS)

### Scenario 2: No Developer Mode (Auto-Fallback)

**Output:**
```bash
🔗 Creating dependency symlinks...
  ⚠️  Windows: Symlinks require Developer Mode
     Falling back to junction points...
  ✓ azure_bootstrap/aws_account -> aws_account (junction)
  ✓ azure_bootstrap/aws_ou -> aws_ou (junction)
```

**Creates:** Junction points (Windows alternative)

### Scenario 3: Fallback Failed (Rare)

**Output:**
```bash
🔗 Creating dependency symlinks...
  ⚠️  Symlinks not supported
     Use .git-pm.env instead
```

**Alternative:** Use environment variables

## 🚀 Quick Setup (Optional)

### Enable Developer Mode for True Symlinks

**Windows 10/11:**
1. Settings → Update & Security → For developers
2. Toggle **Developer Mode** ON
3. Restart terminal
4. Run `git-pm install`

**PowerShell (Admin):**
```powershell
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock" /t REG_DWORD /f /v "AllowDevelopmentWithoutDevLicense" /d "1"
```

## 🎓 Key Points

| Feature | Symlinks | Junction Points |
|---------|----------|-----------------|
| **Privileges** | Admin or Dev Mode | None needed |
| **Terraform** | ✅ Works | ✅ Works |
| **Git** | ✅ Works | ✅ Works |
| **Portable** | Relative paths | Absolute paths |
| **Automatic** | If Dev Mode | Always available |

**Bottom line:** Both work perfectly with Terraform! 🎉

## 🔍 What Are Junction Points?

Junction points are Windows-specific directory links:

```
Link:   .git-packages/packageB/.git-packages/packageA
Target: C:\path\to\.git-packages\packageA (absolute)
```

**Key difference:** Junctions use absolute paths, but Terraform doesn't care!

```hcl
# Your code (same either way)
module "dep" {
  source = ".git-packages/packageA"
}

# With symlink: Relative path resolution
# With junction: Absolute path resolution
# Both work identically! ✅
```

## ✅ No Action Required!

**git-pm automatically:**
1. Tests if symlinks are available
2. Falls back to junctions if needed
3. Provides clear messages
4. Everything just works!

## 🧪 Test It

```bash
# Install with automatic Windows handling
git-pm install

# Verify (PowerShell)
Get-Item .git-packages\packageB\.git-packages\packageA | Select-Object LinkType
# Output: SymbolicLink (Dev Mode) or Junction (fallback)

# Test Terraform
cd .git-packages/packageB
terraform init
# Should work perfectly! ✅
```

## 🛠️ Troubleshooting

### "WinError 1314" in Output

**This is normal!** git-pm detected the error and automatically fell back to junction points. Your installation still works!

### Junctions Don't Work Across Drives

**Cause:** Junctions can't link C: → D:

**Solution:** Enable Developer Mode (symlinks can span drives)

### Git Shows Symlinks as Modified

**Solution:**
```bash
git config --global core.symlinks true
git reset --hard
```

## 📝 Summary

**Windows symlinks:** ✅ Fully supported  
**Privileges needed:** None (uses junctions)  
**Developer Mode:** Optional (enables true symlinks)  
**Terraform compatibility:** 100% with both  
**Manual setup:** None required  

**Everything is automatic!** Just run `git-pm install` and it works. 🎉

---

**Recommendation:** Enable Developer Mode for the best experience, but it's not required - junctions work great too!
