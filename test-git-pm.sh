#!/bin/bash
# Test script for git-pm
# This script sets up test scenarios and validates functionality

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$SCRIPT_DIR/test-workspace"
PYTHON="${PYTHON:-python3}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}ℹ $1${NC}"
}

cleanup() {
    print_header "Cleaning up test workspace"
    if [ -d "$TEST_DIR" ]; then
        rm -rf "$TEST_DIR"
        print_success "Removed test workspace"
    fi
}

setup_test_env() {
    print_header "Setting up test environment"
    
    cleanup
    mkdir -p "$TEST_DIR"
    cd "$TEST_DIR"
    
    print_success "Created test workspace: $TEST_DIR"
}

create_mock_repo() {
    local repo_name=$1
    local repo_dir="$TEST_DIR/mock-repos/$repo_name"
    
    print_info "Creating mock repo: $repo_name"
    
    mkdir -p "$repo_dir"
    cd "$repo_dir"
    
    git init
    git config user.email "test@example.com"
    git config user.name "Test User"
    
    # Create some package directories
    mkdir -p packages/utils
    echo "# Utils Package" > packages/utils/README.md
    echo "def hello():\n    return 'Hello from utils'" > packages/utils/utils.py
    
    mkdir -p packages/components
    echo "# Components Package" > packages/components/README.md
    echo "def render():\n    return 'Component'" > packages/components/component.py
    
    git add .
    git commit -m "Initial commit"
    
    # Create a tag
    git tag v1.0.0
    
    # Create a branch
    git checkout -b develop
    echo "# Development version" >> packages/utils/README.md
    git add .
    git commit -m "Dev changes"
    
    git checkout main 2>/dev/null || git checkout master
    
    print_success "Created mock repo with packages"
    
    cd "$TEST_DIR"
}

test_basic_install() {
    print_header "TEST 1: Basic Install"
    
    local project_dir="$TEST_DIR/test-project-1"
    mkdir -p "$project_dir"
    cd "$project_dir"
    
    # Create manifest
    cat > git-pm.yaml << 'EOF'
packages:
  utils:
    repo: file://../mock-repos/test-repo
    path: packages/utils
    ref:
      type: tag
      value: v1.0.0
  
  components:
    repo: file://../mock-repos/test-repo
    path: packages/components
    ref:
      type: branch
      value: main
EOF
    
    print_info "Created manifest with 2 packages"
    
    # Run install
    $PYTHON "$SCRIPT_DIR/git-pm.py" install
    
    # Verify
    if [ -d ".git-packages/utils" ] && [ -d ".git-packages/components" ]; then
        print_success "Packages installed successfully"
    else
        print_error "Packages not found in .git-packages/"
        return 1
    fi
    
    if [ -f "git-pm.lock" ]; then
        print_success "Lockfile created"
    else
        print_error "Lockfile not created"
        return 1
    fi
    
    # Check if files are accessible
    if [ -f ".git-packages/utils/utils.py" ]; then
        print_success "Package files accessible"
    else
        print_error "Package files not accessible"
        return 1
    fi
    
    cd "$TEST_DIR"
}

test_local_override() {
    print_header "TEST 2: Local Override"
    
    local project_dir="$TEST_DIR/test-project-2"
    mkdir -p "$project_dir"
    cd "$project_dir"
    
    # Create a local development directory
    mkdir -p "$TEST_DIR/local-dev/utils"
    echo "def hello():\n    return 'Hello from LOCAL dev'" > "$TEST_DIR/local-dev/utils/utils.py"
    echo "# Local Development Version" > "$TEST_DIR/local-dev/utils/README.md"
    
    # Create manifest
    cat > git-pm.yaml << 'EOF'
packages:
  utils:
    repo: file://../mock-repos/test-repo
    path: packages/utils
    ref:
      type: tag
      value: v1.0.0
EOF
    
    # Create local override
    cat > git-pm.local.yaml << EOF
overrides:
  utils:
    type: local
    path: $TEST_DIR/local-dev/utils
EOF
    
    print_info "Created local override"
    
    # Run install
    $PYTHON "$SCRIPT_DIR/git-pm.py" install
    
    # Verify local version is used
    if [ -L ".git-packages/utils" ]; then
        local link_target=$(readlink ".git-packages/utils")
        if [[ "$link_target" == *"local-dev"* ]]; then
            print_success "Local override applied correctly"
        else
            print_error "Local override not applied"
            return 1
        fi
    else
        print_error "Symlink not created"
        return 1
    fi
    
    cd "$TEST_DIR"
}

test_list_command() {
    print_header "TEST 3: List Command"
    
    local project_dir="$TEST_DIR/test-project-3"
    mkdir -p "$project_dir"
    cd "$project_dir"
    
    # Create simple manifest
    cat > git-pm.yaml << 'EOF'
packages:
  utils:
    repo: file://../mock-repos/test-repo
    path: packages/utils
    ref:
      type: tag
      value: v1.0.0
EOF
    
    # Install
    $PYTHON "$SCRIPT_DIR/git-pm.py" install > /dev/null 2>&1
    
    # Run list
    print_info "Running list command..."
    $PYTHON "$SCRIPT_DIR/git-pm.py" list
    
    print_success "List command executed"
    
    cd "$TEST_DIR"
}

test_update_command() {
    print_header "TEST 4: Update Command"
    
    local project_dir="$TEST_DIR/test-project-4"
    mkdir -p "$project_dir"
    cd "$project_dir"
    
    # Create manifest with branch reference
    cat > git-pm.yaml << 'EOF'
packages:
  utils:
    repo: file://../mock-repos/test-repo
    path: packages/utils
    ref:
      type: branch
      value: develop
EOF
    
    # Install
    $PYTHON "$SCRIPT_DIR/git-pm.py" install > /dev/null 2>&1
    
    # Update the mock repo
    cd "$TEST_DIR/mock-repos/test-repo"
    git checkout develop
    echo "# Updated in develop" >> packages/utils/README.md
    git add .
    git commit -m "Update develop branch"
    git checkout main 2>/dev/null || git checkout master
    
    cd "$project_dir"
    
    # Run update
    print_info "Running update command..."
    $PYTHON "$SCRIPT_DIR/git-pm.py" update
    
    print_success "Update command executed"
    
    cd "$TEST_DIR"
}

test_clean_command() {
    print_header "TEST 5: Clean Command"
    
    local project_dir="$TEST_DIR/test-project-5"
    mkdir -p "$project_dir"
    cd "$project_dir"
    
    # Create manifest and install
    cat > git-pm.yaml << 'EOF'
packages:
  utils:
    repo: file://../mock-repos/test-repo
    path: packages/utils
    ref:
      type: tag
      value: v1.0.0
EOF
    
    $PYTHON "$SCRIPT_DIR/git-pm.py" install > /dev/null 2>&1
    
    # Verify installed
    if [ -d ".git-packages" ]; then
        print_success "Packages installed"
    fi
    
    # Run clean
    print_info "Running clean command..."
    $PYTHON "$SCRIPT_DIR/git-pm.py" clean
    
    # Verify cleaned
    if [ ! -d ".git-packages" ]; then
        print_success "Packages cleaned successfully"
    else
        print_error "Clean command failed"
        return 1
    fi
    
    cd "$TEST_DIR"
}

test_config_hierarchy() {
    print_header "TEST 6: Config Hierarchy"
    
    local project_dir="$TEST_DIR/test-project-6"
    mkdir -p "$project_dir"
    cd "$project_dir"
    
    # Create user config
    mkdir -p ~/.git-pm
    cat > ~/.git-pm/config.yaml << 'EOF'
packages_dir: .my-packages
auto_update_branches: false
EOF
    
    print_info "Created user-level config"
    
    # Create project config that overrides
    mkdir -p .git-pm
    cat > .git-pm/config.yaml << 'EOF'
packages_dir: .git-packages
EOF
    
    print_info "Created project-level config"
    
    # Create manifest
    cat > git-pm.yaml << 'EOF'
packages:
  utils:
    repo: file://../mock-repos/test-repo
    path: packages/utils
    ref:
      type: tag
      value: v1.0.0
EOF
    
    # Install
    $PYTHON "$SCRIPT_DIR/git-pm.py" install
    
    # Verify project config overrode user config
    if [ -d ".git-packages" ] && [ ! -d ".my-packages" ]; then
        print_success "Project config correctly overrode user config"
    else
        print_error "Config hierarchy not working correctly"
        return 1
    fi
    
    # Cleanup user config
    rm -f ~/.git-pm/config.yaml
    
    cd "$TEST_DIR"
}

test_multiple_versions() {
    print_header "TEST 7: Multiple Versions (Same Repo, Different Refs)"
    
    local project_dir="$TEST_DIR/test-project-7"
    mkdir -p "$project_dir"
    cd "$project_dir"
    
    # Create manifest with different refs to same repo
    cat > git-pm.yaml << 'EOF'
packages:
  utils-stable:
    repo: file://../mock-repos/test-repo
    path: packages/utils
    ref:
      type: tag
      value: v1.0.0
  
  utils-dev:
    repo: file://../mock-repos/test-repo
    path: packages/utils
    ref:
      type: branch
      value: develop
EOF
    
    print_info "Created manifest with 2 versions of same package"
    
    # Install
    $PYTHON "$SCRIPT_DIR/git-pm.py" install
    
    # Verify both installed
    if [ -d ".git-packages/utils-stable" ] && [ -d ".git-packages/utils-dev" ]; then
        print_success "Multiple versions installed successfully"
    else
        print_error "Multiple versions not installed"
        return 1
    fi
    
    cd "$TEST_DIR"
}

run_all_tests() {
    print_header "Git-PM Test Suite"
    
    # Setup
    setup_test_env
    create_mock_repo "test-repo"
    
    # Run tests
    local failed=0
    
    test_basic_install || ((failed++))
    test_local_override || ((failed++))
    test_list_command || ((failed++))
    test_update_command || ((failed++))
    test_clean_command || ((failed++))
    test_config_hierarchy || ((failed++))
    test_multiple_versions || ((failed++))
    
    # Summary
    print_header "Test Summary"
    
    local total=7
    local passed=$((total - failed))
    
    echo -e "Tests run: $total"
    echo -e "${GREEN}Passed: $passed${NC}"
    
    if [ $failed -gt 0 ]; then
        echo -e "${RED}Failed: $failed${NC}"
        echo ""
        print_error "Some tests failed!"
        return 1
    else
        echo ""
        print_success "All tests passed!"
        return 0
    fi
}

# Parse arguments
case "${1:-all}" in
    clean)
        cleanup
        ;;
    setup)
        setup_test_env
        create_mock_repo "test-repo"
        ;;
    all)
        run_all_tests
        ;;
    *)
        echo "Usage: $0 {all|clean|setup}"
        echo "  all   - Run all tests (default)"
        echo "  clean - Clean up test workspace"
        echo "  setup - Setup test environment only"
        exit 1
        ;;
esac
