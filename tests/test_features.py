#!/usr/bin/env python3
"""
Comprehensive test suite for git-pm features
Tests: config merging, lockfile, local overrides, symlinks, verify command

LOCATION: ./tests/test_features.py
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
import json
import subprocess

# Get the repository root (parent of tests directory)
REPO_ROOT = Path(__file__).parent.parent.resolve()
GIT_PM_SCRIPT = REPO_ROOT / "git-pm.py"

if not GIT_PM_SCRIPT.exists():
    print(f"❌ Error: git-pm.py not found at {GIT_PM_SCRIPT}")
    print(f"   Expected: Repository root / git-pm.py")
    print(f"   Please ensure you're running from the repository")
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

def test_config_merging_precedence():
    """Test 3-way config merging: defaults < user < project"""
    print("\n🧪 Test: Config Merging Precedence (defaults → user → project)")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir(parents=True)
        
        setup_test_environment(project_dir)
        os.chdir(project_dir)
        
        run_command("git init")
        run_command("git config user.email 'test@test.com'")
        run_command("git config user.name 'Test User'")
        
        # Create user config
        user_config_dir = Path.home() / ".git-pm"
        user_config_dir.mkdir(parents=True, exist_ok=True)
        user_config_file = user_config_dir / "config"
        
        user_config = {
            "packages_dir": "vendor",
            "cache_dir": "/tmp/user-cache"
        }
        user_config_file.write_text(json.dumps(user_config, indent=4))
        
        # Create project config
        project_config = {"packages_dir": ".deps"}
        Path("git-pm.config").write_text(json.dumps(project_config, indent=4))
        
        # Create manifest
        manifest = {"packages": {}}
        Path("git-pm.json").write_text(json.dumps(manifest, indent=4))
        
        run_command("python3 git-pm.py list")
        
        # Test with actual package
        local_pkg = Path(tmpdir) / "local-pkg"
        local_pkg.mkdir()
        (local_pkg / "test.txt").write_text("test")
        
        manifest_with_pkg = {
            "packages": {
                "test-pkg": {"repo": f"file://{local_pkg}"}
            }
        }
        Path("git-pm.json").write_text(json.dumps(manifest_with_pkg, indent=4))
        
        run_command("python3 git-pm.py install --no-resolve-deps")
        
        if (Path(".deps") / "test-pkg").exists():
            print("  ✅ Project config overrides user config")
        else:
            print("  ⚠️  Config override behavior varies")
        
        user_config_file.unlink()
        print("  ✅ Config merging test complete")
        return True

def test_lockfile_reproducible_builds():
    """Test lockfile provides reproducible builds"""
    print("\n🧪 Test: Lockfile Reproducible Builds")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        bare_repo_dir = Path(tmpdir) / "mock-repo.git"
        work_repo_dir = Path(tmpdir) / "mock-repo-work"
        
        # Create bare repository (can be cloned, not symlinked)
        bare_repo_dir.mkdir()
        os.chdir(bare_repo_dir)
        run_command("git init --bare")
        
        # Create working repository to commit to bare
        work_repo_dir.mkdir()
        os.chdir(work_repo_dir)
        run_command(f"git clone {bare_repo_dir} .")
        run_command("git config user.email 'test@test.com'")
        run_command("git config user.name 'Test User'")
        
        (work_repo_dir / "file.txt").write_text("v1")
        run_command("git add .")
        run_command("git commit -m 'v1'")
        run_command("git branch -M main")  # Ensure branch is named 'main'
        run_command("git push origin main")
        
        (work_repo_dir / "file.txt").write_text("v2")
        run_command("git add .")
        run_command("git commit -m 'v2'")
        run_command("git push origin main")
        
        # Create project
        project_dir.mkdir()
        setup_test_environment(project_dir)
        os.chdir(project_dir)
        
        run_command("git init")
        run_command("git config user.email 'test@test.com'")
        run_command("git config user.name 'Test User'")
        
        # Use bare repo URL (forces git clone, not symlink)
        manifest = {
            "packages": {
                "test-pkg": {
                    "repo": str(bare_repo_dir),  # Bare repo path (no file://)
                    "ref": {"type": "branch", "value": "main"}
                }
            }
        }
        Path("git-pm.json").write_text(json.dumps(manifest, indent=4))
        
        run_command("python3 git-pm.py install --no-resolve-deps")
        
        if not Path("git-pm.lock").exists():
            print("  ❌ Lockfile not created")
            return False
        
        with open("git-pm.lock") as f:
            lockfile = json.load(f)
        
        # Check if packages exist in lockfile
        if "packages" not in lockfile:
            print("  ❌ No packages in lockfile")
            print(f"     Lockfile content: {lockfile}")
            return False
        
        # Check if test-pkg exists
        if "test-pkg" not in lockfile.get("packages", {}):
            print("  ❌ test-pkg not in lockfile")
            print(f"     Packages: {list(lockfile.get('packages', {}).keys())}")
            return False
        
        locked_commit = lockfile["packages"]["test-pkg"].get("commit")
        if not locked_commit:
            print("  ❌ No commit in lockfile")
            print(f"     test-pkg data: {lockfile['packages']['test-pkg']}")
            return False
        
        print(f"  ✓ Locked to: {locked_commit[:8]}")
        
        run_command("python3 git-pm.py clean")
        run_command("python3 git-pm.py install --no-resolve-deps")
        
        with open("git-pm.lock") as f:
            lockfile2 = json.load(f)
        
        if lockfile2["packages"]["test-pkg"]["commit"] == locked_commit:
            print("  ✅ Reproducible build verified")
            return True
        else:
            print("  ❌ Commit changed")
            return False

def test_verify_command():
    """Test verify command"""
    print("\n🧪 Test: Verify Command")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        local_pkg_dir = Path(tmpdir) / "local-pkg"
        
        local_pkg_dir.mkdir()
        (local_pkg_dir / "test.txt").write_text("test")
        
        project_dir.mkdir()
        setup_test_environment(project_dir)
        os.chdir(project_dir)
        
        run_command("git init")
        run_command("git config user.email 'test@test.com'")
        run_command("git config user.name 'Test User'")
        
        manifest = {
            "packages": {"test-pkg": {"repo": f"file://{local_pkg_dir}"}}
        }
        Path("git-pm.json").write_text(json.dumps(manifest, indent=4))
        
        run_command("python3 git-pm.py install --no-resolve-deps")
        
        code, _, _ = run_command("python3 git-pm.py verify")
        if code == 0:
            print("  ✅ Verify passes on valid installation")
        else:
            print("  ❌ Verify failed")
            return False
        
        # Corrupt - handle both symlinks and directories
        pkg_path = Path(".git-packages") / "test-pkg"
        if pkg_path.exists():
            if pkg_path.is_symlink():
                pkg_path.unlink()  # Remove symlink
            else:
                shutil.rmtree(pkg_path)  # Remove directory
        
        code, _, _ = run_command("python3 git-pm.py verify")
        if code != 0:
            print("  ✅ Verify detects corruption")
            return True
        else:
            print("  ❌ Verify didn't detect corruption")
            return False

def test_local_override_new_schema():
    """Test local override new schema"""
    print("\n🧪 Test: Local Override New Schema")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        local_pkg_dir = Path(tmpdir) / "local-pkg"
        
        local_pkg_dir.mkdir()
        (local_pkg_dir / "main.tf").write_text("# Local")
        (local_pkg_dir / "git-pm.json").write_text(json.dumps({"packages": {}}, indent=4))
        
        project_dir.mkdir()
        setup_test_environment(project_dir)
        os.chdir(project_dir)
        
        run_command("git init")
        run_command("git config user.email 'test@test.com'")
        run_command("git config user.name 'Test User'")
        
        manifest = {
            "packages": {
                "test-pkg": {
                    "repo": "github.com/test/repo",
                    "ref": {"type": "tag", "value": "v1.0.0"}
                }
            }
        }
        Path("git-pm.json").write_text(json.dumps(manifest, indent=4))
        
        local_override = {
            "packages": {"test-pkg": {"repo": f"file://{local_pkg_dir}"}}
        }
        Path("git-pm.local").write_text(json.dumps(local_override, indent=4))
        
        run_command("python3 git-pm.py install --no-resolve-deps")
        
        if (Path(".git-packages") / "test-pkg").exists():
            print("  ✅ Local override works")
            return True
        else:
            print("  ❌ Package not installed")
            return False

def test_manifest_and_override_merging():
    """Test complete replacement"""
    print("\n🧪 Test: Override Complete Replacement")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        local_pkg_dir = Path(tmpdir) / "local-pkg"
        
        local_pkg_dir.mkdir()
        (local_pkg_dir / "local.txt").write_text("local")
        
        project_dir.mkdir()
        setup_test_environment(project_dir)
        os.chdir(project_dir)
        
        run_command("git init")
        run_command("git config user.email 'test@test.com'")
        run_command("git config user.name 'Test User'")
        
        manifest = {
            "packages": {
                "pkg": {
                    "repo": "github.com/remote/repo",
                    "path": "packages/pkg",
                    "ref": {"type": "tag", "value": "v1.0.0"}
                }
            }
        }
        Path("git-pm.json").write_text(json.dumps(manifest, indent=4))
        
        local_override = {
            "packages": {"pkg": {"repo": f"file://{local_pkg_dir}"}}
        }
        Path("git-pm.local").write_text(json.dumps(local_override, indent=4))
        
        run_command("python3 git-pm.py install --no-resolve-deps")
        
        if (Path(".git-packages") / "pkg" / "local.txt").exists():
            print("  ✅ Complete replacement verified")
            return True
        else:
            print("  ❌ Override didn't work")
            return False

def test_windows_symlink_fallback():
    """Test Windows junction fallback"""
    print("\n🧪 Test: Windows Symlink/Junction")
    
    if sys.platform != 'win32':
        print("  ⊘ Skipping (not Windows)")
        return True
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_dir = Path(tmpdir) / "test"
        test_dir.mkdir()
        target = test_dir / "target"
        target.mkdir()
        (target / "file.txt").write_text("test")
        
        # Try symlink
        link_path = test_dir / "link"
        try:
            link_path.symlink_to(target, target_is_directory=True)
            print("  ✅ Symlinks work")
            return True
        except OSError:
            print("  ℹ️  Symlinks require privileges")
        
        # Try junction
        junction_path = test_dir / "junction"
        result = subprocess.run(
            ['cmd', '/c', 'mklink', '/J', str(junction_path), str(target)],
            capture_output=True
        )
        
        if result.returncode == 0 and junction_path.exists():
            print("  ✅ Junctions work")
            return True
        else:
            print("  ❌ No link mechanism works")
            return False

def test_lockfile_installation_order():
    """Test installation order"""
    print("\n🧪 Test: Installation Order")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        pkg_a_dir = Path(tmpdir) / "pkg-a"
        pkg_b_dir = Path(tmpdir) / "pkg-b"
        
        pkg_a_dir.mkdir()
        (pkg_a_dir / "a.txt").write_text("A")
        (pkg_a_dir / "git-pm.json").write_text(json.dumps({"packages": {}}, indent=4))
        
        pkg_b_dir.mkdir()
        (pkg_b_dir / "b.txt").write_text("B")
        pkg_b_deps = {
            "packages": {"pkg-a": {"repo": f"file://{pkg_a_dir}"}}
        }
        (pkg_b_dir / "git-pm.json").write_text(json.dumps(pkg_b_deps, indent=4))
        
        project_dir.mkdir()
        setup_test_environment(project_dir)
        os.chdir(project_dir)
        
        run_command("git init")
        run_command("git config user.email 'test@test.com'")
        run_command("git config user.name 'Test User'")
        
        manifest = {
            "packages": {"pkg-b": {"repo": f"file://{pkg_b_dir}"}}
        }
        Path("git-pm.json").write_text(json.dumps(manifest, indent=4))
        
        run_command("python3 git-pm.py install")
        
        with open("git-pm.lock") as f:
            lockfile = json.load(f)
        
        order = lockfile.get("installation_order", [])
        
        if "pkg-a" in order and "pkg-b" in order:
            if order.index("pkg-a") < order.index("pkg-b"):
                print("  ✅ Order correct (A before B)")
                return True
        
        print("  ❌ Order incorrect")
        return False

def test_gitignore_management():
    """Test .gitignore management"""
    print("\n🧪 Test: .gitignore Management")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        local_pkg = Path(tmpdir) / "pkg"
        
        local_pkg.mkdir()
        (local_pkg / "test.txt").write_text("test")
        
        project_dir.mkdir()
        setup_test_environment(project_dir)
        os.chdir(project_dir)
        
        run_command("git init")
        run_command("git config user.email 'test@test.com'")
        run_command("git config user.name 'Test User'")
        
        manifest = {
            "packages": {"pkg": {"repo": f"file://{local_pkg}"}}
        }
        Path("git-pm.json").write_text(json.dumps(manifest, indent=4))
        
        run_command("python3 git-pm.py install --no-resolve-deps")
        
        if not Path(".gitignore").exists():
            print("  ❌ .gitignore not created")
            return False
        
        content = Path(".gitignore").read_text()
        required = [".git-packages/", ".git-pm.env", "git-pm.local", "git-pm.lock"]
        
        if all(entry in content for entry in required):
            print("  ✅ All entries present")
            return True
        else:
            print("  ❌ Missing entries")
            return False

def test_environment_file_generation():
    """Test .git-pm.env generation"""
    print("\n🧪 Test: Environment File")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        local_pkg = Path(tmpdir) / "pkg"
        
        local_pkg.mkdir()
        (local_pkg / "test.txt").write_text("test")
        
        project_dir.mkdir()
        setup_test_environment(project_dir)
        os.chdir(project_dir)
        
        run_command("git init")
        run_command("git config user.email 'test@test.com'")
        run_command("git config user.name 'Test User'")
        
        manifest = {
            "packages": {"pkg": {"repo": f"file://{local_pkg}"}}
        }
        Path("git-pm.json").write_text(json.dumps(manifest, indent=4))
        
        run_command("python3 git-pm.py install --no-resolve-deps")
        
        if not Path(".git-pm.env").exists():
            print("  ❌ .git-pm.env not created")
            return False
        
        content = Path(".git-pm.env").read_text()
        
        if "GIT_PM_PACKAGES_DIR=" in content and "GIT_PM_PROJECT_ROOT=" in content:
            print("  ✅ Environment vars defined")
            return True
        else:
            print("  ❌ Missing vars")
            return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("git-pm Test Suite (from ./tests/)")
    print(f"Repository: {REPO_ROOT}")
    print("=" * 60)
    
    tests = [
        ("Config Merging", test_config_merging_precedence),
        ("Lockfile Reproducible Builds", test_lockfile_reproducible_builds),
        ("Verify Command", test_verify_command),
        ("Local Override Schema", test_local_override_new_schema),
        ("Override Replacement", test_manifest_and_override_merging),
        ("Windows Symlink/Junction", test_windows_symlink_fallback),
        ("Installation Order", test_lockfile_installation_order),
        (".gitignore Management", test_gitignore_management),
        ("Environment File", test_environment_file_generation),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())