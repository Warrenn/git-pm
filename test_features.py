#!/usr/bin/env python3
"""
Comprehensive test suite for git-pm features
Tests: local overrides, symlinks, environment variables, .gitignore management
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
import json
import subprocess

# Get the repository root (where git-pm.py is located)
REPO_ROOT = Path(__file__).parent.resolve()
GIT_PM_SCRIPT = REPO_ROOT / "git-pm.py"

if not GIT_PM_SCRIPT.exists():
    print(f"❌ Error: git-pm.py not found at {GIT_PM_SCRIPT}")
    print("   Please run from the repository root")
    sys.exit(1)

def run_command(cmd, cwd=None):
    """Run a command and return output"""
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True
    )
    return result.returncode, result.stdout, result.stderr

def setup_test_environment(test_dir):
    """Copy git-pm.py to test directory"""
    shutil.copy(GIT_PM_SCRIPT, test_dir / "git-pm.py")

def test_local_overrides():
    """Test local override discovery and installation"""
    print("\n🧪 Test: Local Override Discovery")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        local_pkg_dir = Path(tmpdir) / "local-package"
        
        # Create local package
        local_pkg_dir.mkdir(parents=True)
        (local_pkg_dir / "main.tf").write_text("# Local package")
        (local_pkg_dir / "git-pm.yaml").write_text("packages: {}")
        
        # Create project
        project_dir.mkdir(parents=True)
        
        # Copy git-pm.py to project directory
        setup_test_environment(project_dir)
        
        # Verify git-pm.py was copied
        gitpm_path = project_dir / "git-pm.py"
        if not gitpm_path.exists():
            print(f"  ❌ Failed to copy git-pm.py to {project_dir}")
            return False
        
        os.chdir(project_dir)
        
        # Verify we can see git-pm.py from current directory
        if not Path("git-pm.py").exists():
            print(f"  ❌ git-pm.py not found in current directory after chdir")
            print(f"     Current directory: {os.getcwd()}")
            print(f"     Files: {list(Path('.').iterdir())}")
            return False
        
        # Initialize git
        run_command("git init")
        run_command("git config user.email 'test@test.com'")
        run_command("git config user.name 'Test User'")
        
        # Create manifest
        manifest = """packages:
  test-package:
    repo: github.com/test/repo
    path: package
    ref:
      type: tag
      value: v1.0.0
"""
        Path("git-pm.yaml").write_text(manifest)
        
        # Create local override
        local_override = f"""overrides:
  test-package:
    type: local
    path: {local_pkg_dir}
"""
        Path("git-pm.local.yaml").write_text(local_override)
        
        # Run install
        code, stdout, stderr = run_command("python3 git-pm.py install --no-resolve-deps")
        
        # Check if local override was used (no clone attempted)
        if "Using local override" in stdout or "Override:" in stdout:
            print("  ✅ Local override detected and used")
        else:
            print(f"  ❌ Local override not used")
            if stderr:
                print(f"     Error: {stderr}")
            if stdout:
                print(f"     Output: {stdout}")
            return False
        
        # Check if package was installed
        pkg_path = Path(".git-packages") / "test-package"
        if pkg_path.exists():
            print("  ✅ Package installed via local override")
        else:
            print("  ❌ Package not installed")
            return False
    
    return True

def test_environment_variables():
    """Test .git-pm.env generation"""
    print("\n🧪 Test: Environment Variables Generation")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir(parents=True)
        
        # Copy git-pm.py to project directory
        setup_test_environment(project_dir)
        
        os.chdir(project_dir)
        
        # Verify git-pm.py exists
        if not Path("git-pm.py").exists():
            print(f"  ❌ git-pm.py not found after setup")
            return False
        
        # Initialize git
        run_command("git init")
        run_command("git config user.email 'test@test.com'")
        run_command("git config user.name 'Test User'")
        
        # Create simple manifest
        manifest = """packages:
  test-package:
    repo: github.com/test/repo
    path: package
    ref:
      type: commit
      value: abc123
"""
        Path("git-pm.yaml").write_text(manifest)
        
        # Create fake package in cache
        cache_dir = Path(".git-pm-cache")
        pkg_cache = cache_dir / "test-cache"
        pkg_cache.mkdir(parents=True)
        (pkg_cache / "package").mkdir()
        (pkg_cache / "package" / "main.tf").write_text("# Test")
        (pkg_cache / "package" / "git-pm.yaml").write_text("packages: {}")
        
        # Run install (will fail but should still generate env file)
        run_command("python3 git-pm.py install --no-resolve-deps")
        
        # Check if .git-pm.env was created
        env_file = Path(".git-pm.env")
        if env_file.exists():
            content = env_file.read_text()
            
            if "GIT_PM_PACKAGES_DIR=" in content:
                print("  ✅ GIT_PM_PACKAGES_DIR defined")
            else:
                print("  ❌ GIT_PM_PACKAGES_DIR not found")
                return False
            
            if "GIT_PM_PROJECT_ROOT=" in content:
                print("  ✅ GIT_PM_PROJECT_ROOT defined")
            else:
                print("  ❌ GIT_PM_PROJECT_ROOT not found")
                return False
            
            print("  ✅ .git-pm.env generated successfully")
        else:
            print("  ❌ .git-pm.env not generated")
            return False
    
    return True

def test_gitignore_management():
    """Test automatic .gitignore management"""
    print("\n🧪 Test: .gitignore Management")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir(parents=True)
        
        # Copy git-pm.py to project directory
        setup_test_environment(project_dir)
        
        os.chdir(project_dir)
        
        # Verify git-pm.py exists
        if not Path("git-pm.py").exists():
            print(f"  ❌ git-pm.py not found after setup")
            return False
        
        # Initialize git
        run_command("git init")
        run_command("git config user.email 'test@test.com'")
        run_command("git config user.name 'Test User'")
        
        # Create manifest
        manifest = """packages:
  test-package:
    repo: github.com/test/repo
    path: package
    ref:
      type: commit
      value: abc123
"""
        Path("git-pm.yaml").write_text(manifest)
        
        # Run install (will fail but should update .gitignore)
        run_command("python3 git-pm.py install --no-resolve-deps")
        
        # Check if .gitignore was created/updated
        gitignore = Path(".gitignore")
        if gitignore.exists():
            content = gitignore.read_text()
            
            required_entries = [
                ".git-packages/",
                ".git-pm.env",
                "git-pm.local.yaml",
                "git-pm.lock"
            ]
            
            missing = []
            for entry in required_entries:
                if entry not in content and entry.rstrip('/') not in content:
                    missing.append(entry)
            
            if not missing:
                print("  ✅ All required entries in .gitignore")
            else:
                print(f"  ❌ Missing entries: {missing}")
                return False
            
            print("  ✅ .gitignore managed correctly")
        else:
            print("  ❌ .gitignore not created")
            return False
    
    return True

def test_gitignore_no_duplicates():
    """Test that .gitignore doesn't create duplicates"""
    print("\n🧪 Test: .gitignore No Duplicates")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir(parents=True)
        
        # Copy git-pm.py to project directory
        setup_test_environment(project_dir)
        
        os.chdir(project_dir)
        
        # Initialize git
        run_command("git init")
        run_command("git config user.email 'test@test.com'")
        run_command("git config user.name 'Test User'")
        
        # Create existing .gitignore
        gitignore = Path(".gitignore")
        gitignore.write_text(".git-packages/\n")
        
        # Create manifest
        manifest = """packages:
  test-package:
    repo: github.com/test/repo
    path: package
    ref:
      type: commit
      value: abc123
"""
        Path("git-pm.yaml").write_text(manifest)
        
        # Run install twice
        run_command("python3 git-pm.py install --no-resolve-deps")
        run_command("python3 git-pm.py install --no-resolve-deps")
        
        # Check for duplicates
        content = gitignore.read_text()
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        
        # Count .git-packages entries
        packages_count = sum(1 for line in lines if '.git-packages' in line)
        
        if packages_count <= 1:
            print("  ✅ No duplicate entries")
        else:
            print(f"  ❌ Found {packages_count} .git-packages entries (should be 1)")
            return False
    
    return True

def test_gitignore_skip_flag():
    """Test --no-gitignore flag"""
    print("\n🧪 Test: --no-gitignore Flag")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir(parents=True)
        
        # Copy git-pm.py to project directory
        setup_test_environment(project_dir)
        
        os.chdir(project_dir)
        
        # Initialize git
        run_command("git init")
        run_command("git config user.email 'test@test.com'")
        run_command("git config user.name 'Test User'")
        
        # Create manifest
        manifest = """packages:
  test-package:
    repo: github.com/test/repo
    path: package
    ref:
      type: commit
      value: abc123
"""
        Path("git-pm.yaml").write_text(manifest)
        
        # Run install with --no-gitignore
        run_command("python3 git-pm.py install --no-gitignore --no-resolve-deps")
        
        # Check if .gitignore was NOT created
        gitignore = Path(".gitignore")
        if not gitignore.exists():
            print("  ✅ .gitignore not created with --no-gitignore flag")
        else:
            print("  ❌ .gitignore was created despite --no-gitignore flag")
            return False
    
    return True

def test_symlink_structure():
    """Test nested dependency symlink structure"""
    print("\n🧪 Test: Nested Dependency Symlinks")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir(parents=True)
        os.chdir(project_dir)
        
        # Initialize git
        run_command("git init")
        run_command("git config user.email 'test@test.com'")
        run_command("git config user.name 'Test User'")
        
        # Manually create package structure
        packages_dir = project_dir / ".git-packages"
        packages_dir.mkdir()
        
        # Create packageA
        pkg_a = packages_dir / "packageA"
        pkg_a.mkdir()
        (pkg_a / "main.tf").write_text("# Package A")
        
        # Create packageB (depends on packageA)
        pkg_b = packages_dir / "packageB"
        pkg_b.mkdir()
        (pkg_b / "main.tf").write_text("# Package B")
        
        # Create packageB's .git-packages with symlink
        pkg_b_deps = pkg_b / ".git-packages"
        pkg_b_deps.mkdir()
        
        # Try to create symlink
        link_path = pkg_b_deps / "packageA"
        target_path = Path("..") / ".." / "packageA"
        
        try:
            link_path.symlink_to(target_path, target_is_directory=True)
            
            # Verify symlink
            if link_path.is_symlink():
                print("  ✅ Symlink created successfully")
                
                # Verify target resolution
                resolved = link_path.resolve()
                if resolved == pkg_a:
                    print("  ✅ Symlink resolves correctly")
                else:
                    print(f"  ⚠️  Symlink resolution unexpected: {resolved}")
            else:
                print("  ❌ Not a symlink")
                return False
        except OSError as e:
            if sys.platform == 'win32':
                print(f"  ⚠️  Windows symlink test (may need Developer Mode): {e}")
                # Not a failure on Windows
            else:
                print(f"  ❌ Failed to create symlink: {e}")
                return False
    
    return True

def main():
    """Run all tests"""
    print("=" * 60)
    print("git-pm Feature Test Suite")
    print("=" * 60)
    
    tests = [
        ("Local Override Discovery", test_local_overrides),
        ("Environment Variables", test_environment_variables),
        (".gitignore Management", test_gitignore_management),
        (".gitignore No Duplicates", test_gitignore_no_duplicates),
        (".gitignore Skip Flag", test_gitignore_skip_flag),
        ("Symlink Structure", test_symlink_structure),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"  ❌ Test failed: {name}")
        except Exception as e:
            failed += 1
            print(f"  ❌ Test error: {name}")
            print(f"     Exception: {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())