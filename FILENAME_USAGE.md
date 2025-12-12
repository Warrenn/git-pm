# git-pm Filename and Command Usage

## 📝 Filename: git-pm.py

The main script is named **`git-pm.py`** to make it clear it's a Python script.

## 🚀 How to Call It

After installation, you have **3 ways** to use git-pm:

### Option 1: Via Wrapper (Recommended)
```bash
git-pm install
git-pm list
git-pm --version
```

The installers create a wrapper command that calls `git-pm.py`:
- **Linux/macOS:** Shell script wrapper at `~/.local/bin/git-pm`
- **Windows:** Batch file at `%USERPROFILE%\.git-pm\git-pm.bat`

### Option 2: Direct Python Script
```bash
git-pm.py install
git-pm.py list
git-pm.py --version
```

Call the Python script directly (Linux/macOS only, requires shebang).

### Option 3: Explicit Python Call
```bash
python git-pm.py install
python3 git-pm.py install
```

Works everywhere - explicitly call Python interpreter.

## 📁 Installation Layout

### Linux/macOS

```
~/.local/bin/
├── git-pm.py        # Main Python script (with shebang)
└── git-pm           # Wrapper script (calls git-pm.py)
```

**Wrapper contents:**
```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/git-pm.py" "$@"
```

### Windows

```
%USERPROFILE%\.git-pm\
├── git-pm.py        # Main Python script
└── git-pm.bat       # Batch wrapper
```

**Wrapper contents:**
```batch
@echo off
python "%~dp0git-pm.py" %*
```

## ✅ Benefits of This Approach

1. **Clear File Type** - `.py` extension makes it obvious it's Python
2. **Editor Support** - IDEs recognize and highlight Python syntax
3. **Flexible Usage** - Call it 3 different ways
4. **Cross-Platform** - Works on Linux, macOS, Windows
5. **No Confusion** - Everyone knows it's a Python script
6. **Direct Execution** - Can run `python git-pm.py` anywhere

## 🔧 Manual Installation (Alternative)

If you prefer to install manually without the installer:

### Linux/macOS

```bash
# Download
curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/git-pm.py -o git-pm.py

# Make executable
chmod +x git-pm.py

# Move to PATH
mv git-pm.py ~/.local/bin/

# Use
git-pm.py install
# or
python3 git-pm.py install
```

### Windows

```powershell
# Download
Invoke-WebRequest -Uri https://github.com/Warrenn/git-pm/releases/latest/download/git-pm.py -OutFile git-pm.py

# Move to directory in PATH
Move-Item git-pm.py "$env:USERPROFILE\.git-pm\git-pm.py"

# Use
python git-pm.py install
```

## 📋 Verification

After installation, verify all 3 methods work:

### Linux/macOS
```bash
# Method 1: Wrapper
git-pm --version

# Method 2: Direct script
git-pm.py --version

# Method 3: Explicit Python
python3 git-pm.py --version

# All should output: git-pm 0.2.0
```

### Windows
```powershell
# Method 1: Wrapper (batch file)
git-pm --version

# Method 2: Explicit Python
python git-pm.py --version

# Both should output: git-pm 0.2.0
```

## 🎯 Recommendation

**For users:** Use `git-pm` (via wrapper) for convenience.

**For scripts/automation:** Use `python git-pm.py` for reliability.

**For development:** Use `git-pm.py` or `python git-pm.py` to be explicit.

## 📦 GitHub Release Requirements

Upload to GitHub releases with exact filename:
- ✅ **git-pm.py** (not git-pm, not git-pm.py.txt)

The installers download from:
```
https://github.com/Warrenn/git-pm/releases/latest/download/git-pm.py
```

## 🐛 Troubleshooting

### "git-pm: command not found" (Linux/macOS)

**Solution 1:** Use `git-pm.py` instead
```bash
git-pm.py install
```

**Solution 2:** Check PATH
```bash
echo $PATH | grep ".local/bin"
# If not found:
export PATH="$HOME/.local/bin:$PATH"
```

**Solution 3:** Use explicit Python
```bash
python3 ~/.local/bin/git-pm.py install
```

### "git-pm: command not found" (Windows)

**Solution 1:** Use explicit Python
```powershell
python "$env:USERPROFILE\.git-pm\git-pm.py" install
```

**Solution 2:** Check PATH
```powershell
echo $env:Path
# Should include: C:\Users\YourName\.git-pm
```

**Solution 3:** Restart terminal after installation

### "python: command not found"

Install Python 3.7+:
- **Ubuntu/Debian:** `sudo apt install python3`
- **macOS:** `brew install python3`
- **Windows:** https://www.python.org/downloads/

## 💡 Pro Tips

1. **Alias for shorter command (Linux/macOS):**
   ```bash
   echo 'alias gpm="git-pm"' >> ~/.bashrc
   source ~/.bashrc
   gpm install  # Now you can use 'gpm'
   ```

2. **Add to project scripts:**
   ```json
   {
     "scripts": {
       "deps": "python git-pm.py install",
       "update-deps": "python git-pm.py update"
     }
   }
   ```

3. **Use in Makefiles:**
   ```makefile
   install:
       python git-pm.py install
   
   update:
       python git-pm.py update
   ```

4. **Docker/CI usage:**
   ```dockerfile
   RUN curl -fsSL https://github.com/Warrenn/git-pm/releases/latest/download/git-pm.py -o /usr/local/bin/git-pm.py \
       && chmod +x /usr/local/bin/git-pm.py
   
   RUN python /usr/local/bin/git-pm.py install
   ```

## 📊 Summary

| Method | Linux/macOS | Windows | Notes |
|--------|-------------|---------|-------|
| `git-pm` | ✅ | ✅ | Via wrapper, most convenient |
| `git-pm.py` | ✅ | ❌ | Direct script (Linux/macOS only) |
| `python git-pm.py` | ✅ | ✅ | Explicit, works everywhere |

**Bottom line:** Use whichever method you prefer - they all work! 🚀
