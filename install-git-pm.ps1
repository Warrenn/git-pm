# git-pm installer for Windows
# https://github.com/Warrenn/git-pm

param(
    [switch]$System = $false
)

$ErrorActionPreference = "Stop"

$InstallDir = "$env:USERPROFILE\.git-pm"
$ScriptName = "git-pm.py"
$BatchName = "git-pm.bat"
$RepoUrl = "https://github.com/Warrenn/git-pm"
$LatestReleaseUrl = "$RepoUrl/releases/latest/download/git-pm.py"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Type = "Info"
    )
    
    $color = switch ($Type) {
        "Success" { "Green" }
        "Error" { "Red" }
        "Warning" { "Yellow" }
        "Info" { "Cyan" }
        default { "White" }
    }
    
    $symbol = switch ($Type) {
        "Success" { "[OK]" }
        "Error" { "[X]" }
        "Warning" { "[!]" }
        "Info" { "[i]" }
        default { "[-]" }
    }
    
    Write-Host "$symbol $Message" -ForegroundColor $color
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Test-PythonInstalled {
    Write-ColorOutput "Checking Python installation..." "Info"
    
    # Try python, then py launcher
    $pythonCommands = @("python", "py")
    
    foreach ($cmd in $pythonCommands) {
        try {
            $version = & $cmd --version 2>&1 | Select-String -Pattern '\d+\.\d+' | ForEach-Object { $_.Matches.Value }
            if ($version) {
                $versionParts = $version.Split('.')
                $major = [int]$versionParts[0]
                $minor = [int]$versionParts[1]
                
                if ($major -eq 3 -and $minor -ge 8) {
                    $script:PythonCmd = $cmd
                    Write-ColorOutput "Python $version found ($cmd)" "Success"
                    return $true
                }
            }
        } catch {
            continue
        }
    }
    
    Write-ColorOutput "Python 3.8 or higher is required" "Error"
    Write-Host ""
    Write-Host "Please install Python 3.8+ from:"
    Write-Host "  https://www.python.org/downloads/"
    Write-Host ""
    Write-Host "Make sure to check 'Add Python to PATH' during installation"
    return $false
}

function Test-GitInstalled {
    Write-ColorOutput "Checking git installation..." "Info"
    
    try {
        $version = git --version 2>&1 | Select-String -Pattern '\d+\.\d+' | ForEach-Object { $_.Matches.Value }
        if ($version) {
            Write-ColorOutput "git $version found" "Success"
            return $true
        }
    } catch {
        Write-ColorOutput "git is required" "Error"
        Write-Host ""
        Write-Host "Please install git from:"
        Write-Host "  https://git-scm.com/download/win"
        return $false
    }
    
    return $false
}

function Get-GitPm {
    Write-ColorOutput "Downloading git-pm..." "Info"
    
    $tempFile = [System.IO.Path]::GetTempFileName()
    
    try {
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $LatestReleaseUrl -OutFile $tempFile -UseBasicParsing
        Write-ColorOutput "Downloaded git-pm" "Success"
        return $tempFile
    } catch {
        Write-ColorOutput "Failed to download git-pm from $LatestReleaseUrl" "Error"
        Write-ColorOutput "Error: $_" "Error"
        if (Test-Path $tempFile) {
            Remove-Item $tempFile -Force
        }
        return $null
    }
}

function Install-GitPm {
    Write-ColorOutput "Installing git-pm to $InstallDir..." "Info"
    
    # Create install directory
    if (-not (Test-Path $InstallDir)) {
        New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
    }
    
    # Download
    $tempFile = Get-GitPm
    if (-not $tempFile) {
        return $false
    }
    
    # Install Python script
    $scriptPath = Join-Path $InstallDir $ScriptName
    Move-Item $tempFile $scriptPath -Force
    
    # Create batch wrapper
    $batPath = Join-Path $InstallDir $BatchName
    $batContent = @"
@echo off
python "%~dp0$ScriptName" %*
"@
    Set-Content -Path $batPath -Value $batContent -Encoding ASCII
    
    Write-ColorOutput "Installed to $InstallDir" "Success"
    Write-ColorOutput "You can use 'git-pm' command (calls git-pm.py)" "Info"
    return $true
}

function Test-PathContains {
    param([string]$Directory)
    
    if ($System) {
        $path = [Environment]::GetEnvironmentVariable("PATH", "Machine")
    } else {
        $path = [Environment]::GetEnvironmentVariable("PATH", "User")
    }
    
    return $path -split ';' | Where-Object { $_ -eq $Directory }
}

function Add-ToPath {
    param([string]$Directory)
    
    Write-ColorOutput "Adding $Directory to PATH..." "Info"
    
    if ($System) {
        if (-not (Test-Administrator)) {
            Write-ColorOutput "Administrator privileges required for -System flag" "Error"
            Write-Host ""
            Write-Host "Please run PowerShell as Administrator or omit -System flag"
            return $false
        }
        
        $scope = "Machine"
        $scopeName = "System"
    } else {
        $scope = "User"
        $scopeName = "User"
    }
    
    # Check if already in PATH
    if (Test-PathContains $Directory) {
        Write-ColorOutput "$Directory is already in $scopeName PATH" "Info"
        return $true
    }
    
    try {
        # Get current PATH
        $currentPath = [Environment]::GetEnvironmentVariable("PATH", $scope)
        
        # Add directory to PATH
        if ($currentPath) {
            $newPath = "$currentPath;$Directory"
        } else {
            $newPath = $Directory
        }
        
        [Environment]::SetEnvironmentVariable("PATH", $newPath, $scope)
        
        # Update current session
        $env:Path = "$env:Path;$Directory"
        
        Write-ColorOutput "Added to $scopeName PATH" "Success"
        Write-ColorOutput "Restart your terminal to apply changes" "Info"
        return $true
    } catch {
        Write-ColorOutput "Failed to update PATH: $_" "Error"
        return $false
    }
}

function Test-Installation {
    Write-ColorOutput "Verifying installation..." "Info"
    
    # Refresh environment
    $env:Path = [Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [Environment]::GetEnvironmentVariable("PATH", "User")
    
    try {
        # Try git-pm.bat first (wrapper)
        $version = & "git-pm" --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "git-pm is installed and working: $version" "Success"
            Write-ColorOutput "You can use 'git-pm' command" "Info"
            return $true
        }
    } catch {
        # Try git-pm.py directly
        try {
            $scriptPath = Join-Path $InstallDir $ScriptName
            $version = python $scriptPath --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-ColorOutput "git-pm.py is installed and working: $version" "Success"
                Write-ColorOutput "You can use: python $scriptPath" "Info"
                return $true
            }
        } catch {
            Write-ColorOutput "git-pm command not found" "Error"
            Write-ColorOutput "Please restart your terminal" "Info"
            return $false
        }
    }
    
    return $false
}

function Main {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "git-pm Installer for Windows" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # Check if -System flag requires elevation
    if ($System -and -not (Test-Administrator)) {
        Write-ColorOutput "The -System flag requires administrator privileges" "Warning"
        Write-Host ""
        $response = Read-Host "Continue with user-level installation instead? (Y/n)"
        if ($response -match '^[Nn]') {
            Write-Host ""
            Write-Host "Installation cancelled. To install system-wide, run:"
            Write-Host "  PowerShell as Administrator, then:"
            Write-Host "  irm https://raw.githubusercontent.com/Warrenn/git-pm/main/install-git-pm.ps1 | iex -System"
            exit 1
        }
        $script:System = $false
    }
    
    # Check requirements
    if (-not (Test-PythonInstalled)) {
        exit 1
    }
    
    if (-not (Test-GitInstalled)) {
        exit 1
    }
    
    Write-Host ""
    
    # Install
    if (-not (Install-GitPm)) {
        exit 1
    }
    
    Write-Host ""
    
    # Update PATH
    if (-not (Test-PathContains $InstallDir)) {
        Write-Host ""
        $scope = if ($System) { "system" } else { "user" }
        $response = Read-Host "Add $InstallDir to $scope PATH? (Y/n)"
        if ($response -notmatch '^[Nn]') {
            if (-not (Add-ToPath $InstallDir)) {
                Write-ColorOutput "PATH update failed" "Warning"
                Write-Host ""
                Write-Host "You can manually add to PATH:"
                Write-Host "  1. Search for 'Environment Variables' in Windows"
                Write-Host "  2. Edit 'Path' variable"
                Write-Host "  3. Add: $InstallDir"
            }
        } else {
            Write-ColorOutput "Skipped PATH configuration" "Info"
            Write-Host ""
            Write-Host "To use git-pm, either:"
            Write-Host "  1. Add $InstallDir to your PATH manually"
            Write-Host "  2. Run: $InstallDir\git-pm.bat"
        }
    } else {
        Write-ColorOutput "$InstallDir is already in PATH" "Success"
    }
    
    Write-Host ""
    
    # Verify
    Test-Installation
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "Installation complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Cyan
    Write-Host "  git-pm install          # Install packages with dependency resolution"
    Write-Host "  git-pm add <pkg> <repo> # Add package to manifest"
    Write-Host "  git-pm list             # List installed packages"
    Write-Host "  git-pm --help           # Show all commands"
    Write-Host ""
    Write-Host "Documentation: $RepoUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Note: Restart your terminal if git-pm command is not found" -ForegroundColor Yellow
    Write-Host ""
}

# Run main
try {
    Main
} catch {
    Write-ColorOutput "Installation failed: $_" "Error"
    exit 1
}
