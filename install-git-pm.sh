#!/usr/bin/env bash
# git-pm installer for Linux and macOS
# https://github.com/Warrenn/git-pm

set -e

INSTALL_DIR="$HOME/.local/bin"
SCRIPT_NAME="git-pm.py"
WRAPPER_NAME="git-pm"
REPO_URL="https://github.com/Warrenn/git-pm"
LATEST_RELEASE_URL="$REPO_URL/releases/latest/download/git-pm.py"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_error() {
    echo -e "${RED}✗ $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}" >&2
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}" >&2
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}" >&2
}

check_command() {
    if command -v "$1" >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

check_python() {
    print_info "Checking Python installation..."
    
    # Try python3 first, then python
    for cmd in python3 python; do
        if check_command "$cmd"; then
            version=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)
            
            if [ "$major" -eq 3 ] && [ "$minor" -ge 8 ]; then
                PYTHON_CMD="$cmd"
                print_success "Python $version found ($cmd)"
                return 0
            fi
        fi
    done
    
    print_error "Python 3.8 or higher is required"
    echo "Please install Python 3.8+:"
    echo "  macOS: brew install python3"
    echo "  Ubuntu/Debian: sudo apt install python3"
    echo "  Fedora/RHEL: sudo dnf install python3"
    return 1
}

check_git() {
    print_info "Checking git installation..."
    
    if check_command git; then
        version=$(git --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
        print_success "git $version found"
        return 0
    else
        print_error "git is required"
        echo "Please install git:"
        echo "  macOS: brew install git"
        echo "  Ubuntu/Debian: sudo apt install git"
        echo "  Fedora/RHEL: sudo dnf install git"
        return 1
    fi
}

download_git_pm() {
    print_info "Downloading git-pm..."
    
    local temp_file=$(mktemp)
    
    if check_command curl; then
        if curl -fsSL "$LATEST_RELEASE_URL" -o "$temp_file"; then
            print_success "Downloaded git-pm"
            echo "$temp_file"
            return 0
        fi
    elif check_command wget; then
        if wget -q "$LATEST_RELEASE_URL" -O "$temp_file"; then
            print_success "Downloaded git-pm"
            echo "$temp_file"
            return 0
        fi
    else
        print_error "Neither curl nor wget found"
        echo "Please install curl or wget:"
        echo "  macOS: curl is pre-installed"
        echo "  Ubuntu/Debian: sudo apt install curl"
        echo "  Fedora/RHEL: sudo dnf install curl"
        rm -f "$temp_file"
        return 1
    fi
    
    print_error "Failed to download git-pm from $LATEST_RELEASE_URL"
    rm -f "$temp_file"
    return 1
}

install_git_pm() {
    print_info "Installing git-pm to $INSTALL_DIR..."
    
    # Create install directory
    mkdir -p "$INSTALL_DIR"
    
    # Download
    local temp_file
    temp_file=$(download_git_pm) || return 1
    
    # Install Python script
    local install_path="$INSTALL_DIR/$SCRIPT_NAME"
    mv "$temp_file" "$install_path"
    chmod +x "$install_path"
    
    print_success "Installed to $install_path"
    
    # Create convenience wrapper (git-pm calls git-pm.py)
    local wrapper_path="$INSTALL_DIR/$WRAPPER_NAME"
    cat > "$wrapper_path" << 'EOF'
#!/bin/bash
# git-pm wrapper - calls git-pm.py
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$SCRIPT_DIR/git-pm.py" "$@"
EOF
    chmod +x "$wrapper_path"
    
    print_success "Created wrapper: $wrapper_path"
    print_info "You can use either 'git-pm' or 'git-pm.py' command"
}

check_path() {
    print_info "Checking PATH configuration..."
    
    if echo "$PATH" | grep -q "$INSTALL_DIR"; then
        print_success "$INSTALL_DIR is in PATH"
        return 0
    fi
    
    print_warning "$INSTALL_DIR is not in PATH"
    return 1
}

add_to_path() {
    print_info "Adding $INSTALL_DIR to PATH..."
    
    # Determine shell config file
    local shell_config=""
    if [ -n "$BASH_VERSION" ]; then
        if [ -f "$HOME/.bashrc" ]; then
            shell_config="$HOME/.bashrc"
        elif [ -f "$HOME/.bash_profile" ]; then
            shell_config="$HOME/.bash_profile"
        fi
    elif [ -n "$ZSH_VERSION" ]; then
        shell_config="$HOME/.zshrc"
    elif [ -f "$HOME/.profile" ]; then
        shell_config="$HOME/.profile"
    fi
    
    if [ -z "$shell_config" ]; then
        print_warning "Could not determine shell config file"
        echo "Please add the following to your shell configuration:"
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        return 1
    fi
    
    # Check if already in config
    if grep -q "/.local/bin" "$shell_config" 2>/dev/null; then
        print_info "PATH entry already exists in $shell_config"
        return 0
    fi
    
    # Add to config
    echo "" >> "$shell_config"
    echo "# Added by git-pm installer" >> "$shell_config"
    echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> "$shell_config"
    
    print_success "Added to $shell_config"
    print_info "Run 'source $shell_config' or restart your shell to apply changes"
    
    # Apply to current shell
    export PATH="$HOME/.local/bin:$PATH"
}

verify_installation() {
    print_info "Verifying installation..."
    
    # Check if either command works
    if check_command "$WRAPPER_NAME"; then
        version=$("$WRAPPER_NAME" --version 2>&1)
        print_success "git-pm is installed and working: $version"
        print_info "You can use: 'git-pm' or 'git-pm.py'"
        return 0
    elif check_command "$SCRIPT_NAME"; then
        version=$("$SCRIPT_NAME" --version 2>&1)
        print_success "git-pm.py is installed and working: $version"
        print_info "You can use: 'git-pm.py'"
        return 0
    else
        print_error "git-pm command not found"
        print_info "Try running: source ~/.bashrc  (or restart your terminal)"
        return 1
    fi
}

main() {
    echo "========================================"
    echo "git-pm Installer"
    echo "========================================"
    echo ""
    
    # Check requirements
    if ! check_python; then
        exit 1
    fi
    
    if ! check_git; then
        exit 1
    fi
    
    echo ""
    
    # Install
    if ! install_git_pm; then
        exit 1
    fi
    
    echo ""
    
    # Check and fix PATH
    if ! check_path; then
        echo ""
        read -p "Would you like to add $INSTALL_DIR to your PATH? (y/n) " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            add_to_path
        else
            print_info "Skipped PATH configuration"
            echo "You can manually add this to your shell config:"
            echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        fi
    fi
    
    echo ""
    
    # Verify
    verify_installation
    
    echo ""
    echo "========================================"
    echo "Installation complete!"
    echo "========================================"
    echo ""
    echo "Usage:"
    echo "  git-pm install          # Install packages with dependency resolution"
    echo "  git-pm add <pkg> <repo> # Add package to manifest"
    echo "  git-pm list             # List installed packages"
    echo "  git-pm --help           # Show all commands"
    echo ""
    echo "Documentation: $REPO_URL"
    echo ""
}

main "$@"