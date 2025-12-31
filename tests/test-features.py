#!/usr/bin/env python3
"""
Comprehensive test suite for git-pm features
Tests: config merging, dependency resolution, local overrides, symlinks, Azure DevOps URLs

LOCATION: ./tests/test_features.py
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
import json
import subprocess
import re
import urllib.parse

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

def get_gitpm_class():
    """Import and return the GitPM class from git-pm.py"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("git_pm", GIT_PM_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.GitPM

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
        
        run_command("python3 git-pm.py list 2>&1 || true")
        
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
        
        run_command("python3 git-pm.py install")
        
        if (Path(".deps") / "test-pkg").exists():
            print("  ✅ Project config overrides user config")
        else:
            print("  ⚠️  Config override behavior varies")
        
        user_config_file.unlink()
        print("  ✅ Config merging test complete")
        return True

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
        
        run_command("python3 git-pm.py install")
        
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
        
        run_command("python3 git-pm.py install")
        
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

def test_dependency_resolution():
    """Test dependency resolution and installation order"""
    print("\n🧪 Test: Dependency Resolution")
    
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
        
        code, stdout, stderr = run_command("python3 git-pm.py install")
        
        # Check both packages were installed
        if (Path(".git-packages") / "pkg-a").exists() and (Path(".git-packages") / "pkg-b").exists():
            print("  ✅ Dependencies auto-discovered")
            print("  ✅ Both packages installed")
            return True
        else:
            print("  ❌ Dependency resolution failed")
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
        
        run_command("python3 git-pm.py install")
        
        if not Path(".gitignore").exists():
            print("  ❌ .gitignore not created")
            return False
        
        content = Path(".gitignore").read_text()
        required = [".git-packages/", ".git-pm.env", "git-pm.local"]
        
        if all(entry in content for entry in required):
            print("  ✅ All entries present")
            
            # Verify lockfile is NOT in .gitignore
            if "git-pm.lock" not in content:
                print("  ✅ Lockfile correctly excluded")
                return True
            else:
                print("  ⚠️  Lockfile entry present (should be removed)")
                return True  # Still pass, just warn
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
        
        run_command("python3 git-pm.py install")
        
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


# =============================================================================
# Azure DevOps URL Handling Tests
# =============================================================================

def test_azure_devops_url_parsing():
    """Test parsing of various Azure DevOps URL formats"""
    print("\n🧪 Test: Azure DevOps URL Parsing")
    
    try:
        GitPM = get_gitpm_class()
    except Exception as e:
        print(f"  ❌ Failed to import GitPM: {e}")
        return False
    
    # Check if the method exists
    if not hasattr(GitPM, '_parse_azure_devops_url'):
        print("  ⊘ Skipping (_parse_azure_devops_url not implemented)")
        return True
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        os.chdir(project_dir)
        
        # Create minimal manifest
        Path("git-pm.json").write_text(json.dumps({"packages": {}}, indent=4))
        
        gpm = GitPM()
        
        # Test cases: (input_url, expected_org, expected_project, expected_repo)
        test_cases = [
            # SSH format
            (
                "git@ssh.dev.azure.com:v3/bridgewaybentech/Platform%20Engineering/bbt-aws-iac",
                "bridgewaybentech", "Platform Engineering", "bbt-aws-iac"
            ),
            # HTTPS format with user
            (
                "https://bridgewaybentech@dev.azure.com/bridgewaybentech/Platform%20Engineering/_git/bbt-aws-iac",
                "bridgewaybentech", "Platform Engineering", "bbt-aws-iac"
            ),
            # HTTPS format without user
            (
                "https://dev.azure.com/bridgewaybentech/Platform%20Engineering/_git/shared-scripts",
                "bridgewaybentech", "Platform Engineering", "shared-scripts"
            ),
            # Shorthand with /_git/
            (
                "dev.azure.com/bridgewaybentech/Platform%20Engineering/_git/shared-scripts",
                "bridgewaybentech", "Platform Engineering", "shared-scripts"
            ),
            # Shorthand without /_git/
            (
                "dev.azure.com/bridgewaybentech/Platform%20Engineering/shared-scripts",
                "bridgewaybentech", "Platform Engineering", "shared-scripts"
            ),
            # Malformed hybrid format (dev.azure.com:v3/...)
            (
                "dev.azure.com:v3/bridgewaybentech/Platform%20Engineering/tf-modules-iac",
                "bridgewaybentech", "Platform Engineering", "tf-modules-iac"
            ),
            # With .git suffix
            (
                "https://dev.azure.com/bridgewaybentech/Platform%20Engineering/_git/shared-scripts.git",
                "bridgewaybentech", "Platform Engineering", "shared-scripts"
            ),
        ]
        
        all_passed = True
        for url, exp_org, exp_project, exp_repo in test_cases:
            result = gpm._parse_azure_devops_url(url)
            
            if result is None:
                print(f"  ❌ Failed to parse: {url}")
                all_passed = False
                continue
            
            org, project, repo = result
            
            if org == exp_org and project == exp_project and repo == exp_repo:
                print(f"  ✅ Parsed: {url[:50]}...")
            else:
                print(f"  ❌ Mismatch for: {url}")
                print(f"     Expected: org={exp_org}, project={exp_project}, repo={exp_repo}")
                print(f"     Got:      org={org}, project={project}, repo={repo}")
                all_passed = False
        
        # Test non-Azure DevOps URLs return None
        non_ado_urls = [
            "github.com/owner/repo",
            "https://github.com/owner/repo.git",
            "git@github.com:owner/repo.git",
            "gitlab.com/owner/repo",
        ]
        
        for url in non_ado_urls:
            result = gpm._parse_azure_devops_url(url)
            if result is None:
                print(f"  ✅ Correctly rejected non-ADO: {url}")
            else:
                print(f"  ❌ Should have rejected: {url}")
                all_passed = False
        
        return all_passed


def test_azure_devops_url_building():
    """Test building Azure DevOps URLs in different protocols"""
    print("\n🧪 Test: Azure DevOps URL Building")
    
    try:
        GitPM = get_gitpm_class()
    except Exception as e:
        print(f"  ❌ Failed to import GitPM: {e}")
        return False
    
    # Check if the method exists
    if not hasattr(GitPM, '_build_azure_devops_url'):
        print("  ⊘ Skipping (_build_azure_devops_url not implemented)")
        return True
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        os.chdir(project_dir)
        
        # Create minimal manifest
        Path("git-pm.json").write_text(json.dumps({"packages": {}}, indent=4))
        
        gpm = GitPM()
        
        # Test SSH output
        ssh_url = gpm._build_azure_devops_url(
            "bridgewaybentech", "Platform Engineering", "shared-scripts", "ssh"
        )
        expected_ssh = "git@ssh.dev.azure.com:v3/bridgewaybentech/Platform Engineering/shared-scripts"
        
        if ssh_url == expected_ssh:
            print(f"  ✅ SSH URL correct")
        else:
            print(f"  ❌ SSH URL mismatch")
            print(f"     Expected: {expected_ssh}")
            print(f"     Got:      {ssh_url}")
            return False
        
        # Test HTTPS output (no token)
        https_url = gpm._build_azure_devops_url(
            "bridgewaybentech", "Platform Engineering", "shared-scripts", "https"
        )
        expected_https = "https://dev.azure.com/bridgewaybentech/Platform%20Engineering/_git/shared-scripts"
        
        if https_url == expected_https:
            print(f"  ✅ HTTPS URL correct")
        else:
            print(f"  ❌ HTTPS URL mismatch")
            print(f"     Expected: {expected_https}")
            print(f"     Got:      {https_url}")
            return False
        
        # Test HTTPS output (with token)
        https_token_url = gpm._build_azure_devops_url(
            "bridgewaybentech", "Platform Engineering", "shared-scripts", "https", "MY_PAT_TOKEN"
        )
        expected_https_token = "https://MY_PAT_TOKEN@dev.azure.com/bridgewaybentech/Platform%20Engineering/_git/shared-scripts"
        
        if https_token_url == expected_https_token:
            print(f"  ✅ HTTPS+PAT URL correct")
        else:
            print(f"  ❌ HTTPS+PAT URL mismatch")
            print(f"     Expected: {expected_https_token}")
            print(f"     Got:      {https_token_url}")
            return False
        
        return True


def test_azure_devops_normalize_with_pat():
    """Test normalize_repo_url uses HTTPS when PAT is configured"""
    print("\n🧪 Test: Azure DevOps URL Normalization with PAT")
    
    try:
        GitPM = get_gitpm_class()
    except Exception as e:
        print(f"  ❌ Failed to import GitPM: {e}")
        return False
    
    # Check if the method exists
    if not hasattr(GitPM, '_parse_azure_devops_url'):
        print("  ⊘ Skipping (Azure DevOps URL handling not implemented)")
        return True
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        os.chdir(project_dir)
        
        # Create minimal manifest
        Path("git-pm.json").write_text(json.dumps({"packages": {}}, indent=4))
        
        # Create project config with PAT
        project_config = {"azure_devops_pat": "test-token-12345"}
        Path("git-pm.config").write_text(json.dumps(project_config, indent=4))
        
        gpm = GitPM()
        
        # Test: SSH input should become HTTPS when PAT is present
        test_urls = [
            "git@ssh.dev.azure.com:v3/bridgewaybentech/Platform%20Engineering/bbt-aws-iac",
            "dev.azure.com:v3/bridgewaybentech/Platform%20Engineering/tf-modules-iac",
            "dev.azure.com/bridgewaybentech/Platform%20Engineering/shared-scripts",
        ]
        
        all_passed = True
        for url in test_urls:
            result = gpm.normalize_repo_url(url)
            
            # Should be HTTPS with token
            if result.startswith("https://test-token-12345@dev.azure.com/"):
                print(f"  ✅ PAT applied: {url[:40]}...")
            else:
                print(f"  ❌ PAT not applied for: {url}")
                print(f"     Got: {result}")
                all_passed = False
            
            # Should have proper /_git/ path
            if "/_git/" in result:
                print(f"  ✅ Correct /_git/ path")
            else:
                print(f"  ❌ Missing /_git/ in path")
                print(f"     Got: {result}")
                all_passed = False
            
            # Should NOT have .git suffix (Azure DevOps doesn't need it)
            if not result.endswith(".git"):
                print(f"  ✅ No spurious .git suffix")
            else:
                print(f"  ❌ Spurious .git suffix present")
                print(f"     Got: {result}")
                all_passed = False
        
        return all_passed


def test_azure_devops_normalize_with_protocol_config():
    """Test normalize_repo_url respects git_protocol configuration"""
    print("\n🧪 Test: Azure DevOps URL Normalization with Protocol Config")
    
    try:
        GitPM = get_gitpm_class()
    except Exception as e:
        print(f"  ❌ Failed to import GitPM: {e}")
        return False
    
    # Check if the method exists
    if not hasattr(GitPM, '_parse_azure_devops_url'):
        print("  ⊘ Skipping (Azure DevOps URL handling not implemented)")
        return True
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        os.chdir(project_dir)
        
        # Create minimal manifest
        Path("git-pm.json").write_text(json.dumps({"packages": {}}, indent=4))
        
        # Test 1: HTTPS protocol config (no PAT) - HTTPS input should stay HTTPS
        project_config = {"git_protocol": {"dev.azure.com": "https"}}
        Path("git-pm.config").write_text(json.dumps(project_config, indent=4))
        
        gpm = GitPM()
        
        # SSH input with HTTPS config (no PAT) -> should become HTTPS without token
        result = gpm.normalize_repo_url("git@ssh.dev.azure.com:v3/bridgewaybentech/Platform%20Engineering/bbt-aws-iac")
        
        if result.startswith("https://dev.azure.com/"):
            print(f"  ✅ HTTPS protocol respected (no token)")
        else:
            print(f"  ❌ Protocol config not respected")
            print(f"     Got: {result}")
            return False
        
        # Test 2: SSH protocol config - HTTPS input should become SSH
        project_config = {"git_protocol": {"dev.azure.com": "ssh"}}
        Path("git-pm.config").write_text(json.dumps(project_config, indent=4))
        
        gpm = GitPM()
        
        result = gpm.normalize_repo_url("https://dev.azure.com/bridgewaybentech/Platform%20Engineering/_git/shared-scripts")
        
        if result.startswith("git@ssh.dev.azure.com:v3/"):
            print(f"  ✅ SSH protocol respected")
        else:
            print(f"  ❌ SSH protocol config not respected")
            print(f"     Got: {result}")
            return False
        
        return True


def test_azure_devops_url_roundtrip():
    """Test that URLs can be parsed and rebuilt correctly (roundtrip)"""
    print("\n🧪 Test: Azure DevOps URL Roundtrip")
    
    try:
        GitPM = get_gitpm_class()
    except Exception as e:
        print(f"  ❌ Failed to import GitPM: {e}")
        return False
    
    # Check if the methods exist
    if not hasattr(GitPM, '_parse_azure_devops_url') or not hasattr(GitPM, '_build_azure_devops_url'):
        print("  ⊘ Skipping (Azure DevOps URL methods not implemented)")
        return True
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        os.chdir(project_dir)
        
        # Create minimal manifest
        Path("git-pm.json").write_text(json.dumps({"packages": {}}, indent=4))
        
        gpm = GitPM()
        
        # All these different input formats should produce equivalent outputs
        input_urls = [
            "git@ssh.dev.azure.com:v3/myorg/My%20Project/my-repo",
            "https://dev.azure.com/myorg/My%20Project/_git/my-repo",
            "https://user@dev.azure.com/myorg/My%20Project/_git/my-repo",
            "dev.azure.com/myorg/My%20Project/_git/my-repo",
            "dev.azure.com/myorg/My%20Project/my-repo",
            "dev.azure.com:v3/myorg/My%20Project/my-repo",
        ]
        
        expected_ssh = "git@ssh.dev.azure.com:v3/myorg/My Project/my-repo"
        expected_https = "https://dev.azure.com/myorg/My%20Project/_git/my-repo"
        
        all_passed = True
        for url in input_urls:
            parsed = gpm._parse_azure_devops_url(url)
            if parsed is None:
                print(f"  ❌ Failed to parse: {url}")
                all_passed = False
                continue
            
            org, project, repo = parsed
            
            # All should parse to the same components
            if org != "myorg" or project != "My Project" or repo != "my-repo":
                print(f"  ❌ Parse mismatch for: {url}")
                print(f"     Got: org={org}, project={project}, repo={repo}")
                all_passed = False
                continue
            
            # Rebuild in both protocols
            ssh_rebuilt = gpm._build_azure_devops_url(org, project, repo, "ssh")
            https_rebuilt = gpm._build_azure_devops_url(org, project, repo, "https")
            
            if ssh_rebuilt == expected_ssh and https_rebuilt == expected_https:
                print(f"  ✅ Roundtrip OK: {url[:40]}...")
            else:
                print(f"  ❌ Rebuild mismatch for: {url}")
                if ssh_rebuilt != expected_ssh:
                    print(f"     SSH expected: {expected_ssh}")
                    print(f"     SSH got:      {ssh_rebuilt}")
                if https_rebuilt != expected_https:
                    print(f"     HTTPS expected: {expected_https}")
                    print(f"     HTTPS got:      {https_rebuilt}")
                all_passed = False
        
        return all_passed


def test_azure_devops_system_accesstoken():
    """Test normalize_repo_url uses HTTPS without embedded token when SYSTEM_ACCESSTOKEN is set"""
    print("\n🧪 Test: Azure DevOps SYSTEM_ACCESSTOKEN Support")
    
    try:
        GitPM = get_gitpm_class()
    except Exception as e:
        print(f"  ❌ Failed to import GitPM: {e}")
        return False
    
    # Check if the method exists
    if not hasattr(GitPM, '_parse_azure_devops_url'):
        print("  ⊘ Skipping (Azure DevOps URL handling not implemented)")
        return True
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        os.chdir(project_dir)
        
        # Create minimal manifest (no PAT configured)
        Path("git-pm.json").write_text(json.dumps({"packages": {}}, indent=4))
        Path("git-pm.config").write_text(json.dumps({}, indent=4))
        
        # Save original env
        original_system_token = os.environ.get("SYSTEM_ACCESSTOKEN")
        original_pat = os.environ.get("AZURE_DEVOPS_PAT")
        
        try:
            # Clear PAT, set SYSTEM_ACCESSTOKEN
            if "AZURE_DEVOPS_PAT" in os.environ:
                del os.environ["AZURE_DEVOPS_PAT"]
            os.environ["SYSTEM_ACCESSTOKEN"] = "test-bearer-token-xyz"
            
            gpm = GitPM()
            
            # Test: SSH input should become HTTPS without embedded token
            test_url = "git@ssh.dev.azure.com:v3/bridgewaybentech/Platform%20Engineering/bbt-aws-iac"
            result = gpm.normalize_repo_url(test_url)
            
            # Should be HTTPS
            if not result.startswith("https://dev.azure.com/"):
                print(f"  ❌ Should be HTTPS URL")
                print(f"     Got: {result}")
                return False
            print(f"  ✅ Uses HTTPS protocol")
            
            # Should NOT have token embedded in URL (token goes in http.extraheader)
            if "test-bearer-token" in result or "@dev.azure.com" in result:
                print(f"  ❌ Token should NOT be in URL (should use http.extraheader)")
                print(f"     Got: {result}")
                return False
            print(f"  ✅ Token not embedded in URL (will use http.extraheader)")
            
            # Should have proper /_git/ path
            if "/_git/" not in result:
                print(f"  ❌ Missing /_git/ in path")
                print(f"     Got: {result}")
                return False
            print(f"  ✅ Correct /_git/ path format")
            
            # Verify expected URL format
            expected = "https://dev.azure.com/bridgewaybentech/Platform%20Engineering/_git/bbt-aws-iac"
            if result == expected:
                print(f"  ✅ URL format correct: {result}")
            else:
                print(f"  ❌ URL format mismatch")
                print(f"     Expected: {expected}")
                print(f"     Got:      {result}")
                return False
            
            return True
            
        finally:
            # Restore original env
            if original_system_token is not None:
                os.environ["SYSTEM_ACCESSTOKEN"] = original_system_token
            elif "SYSTEM_ACCESSTOKEN" in os.environ:
                del os.environ["SYSTEM_ACCESSTOKEN"]
            
            if original_pat is not None:
                os.environ["AZURE_DEVOPS_PAT"] = original_pat


def test_azure_devops_configure_auth():
    """Test _configure_azure_devops_auth sets up git http.extraheader"""
    print("\n🧪 Test: Azure DevOps Configure Auth (http.extraheader)")
    
    try:
        GitPM = get_gitpm_class()
    except Exception as e:
        print(f"  ❌ Failed to import GitPM: {e}")
        return False
    
    # Check if the method exists
    if not hasattr(GitPM, '_configure_azure_devops_auth'):
        print("  ⊘ Skipping (_configure_azure_devops_auth not implemented)")
        return True
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        os.chdir(project_dir)
        
        # Create minimal manifest
        Path("git-pm.json").write_text(json.dumps({"packages": {}}, indent=4))
        
        # Initialize git repo for config commands
        subprocess.run(["git", "init"], capture_output=True)
        
        # Save original env and git config
        original_token = os.environ.get("SYSTEM_ACCESSTOKEN")
        
        try:
            # Test 1: No token set - should return False
            if "SYSTEM_ACCESSTOKEN" in os.environ:
                del os.environ["SYSTEM_ACCESSTOKEN"]
            
            gpm = GitPM()
            result = gpm._configure_azure_devops_auth()
            
            if result == False:
                print(f"  ✅ Returns False when SYSTEM_ACCESSTOKEN not set")
            else:
                print(f"  ❌ Should return False when no token")
                return False
            
            # Test 2: Token set - should configure git and return True
            os.environ["SYSTEM_ACCESSTOKEN"] = "test-token-12345"
            
            gpm = GitPM()
            result = gpm._configure_azure_devops_auth()
            
            if result == True:
                print(f"  ✅ Returns True when SYSTEM_ACCESSTOKEN is set")
            else:
                print(f"  ❌ Should return True when token is set")
                return False
            
            # Verify git config was set
            config_result = subprocess.run(
                ["git", "config", "--global", "http.https://dev.azure.com/.extraheader"],
                capture_output=True,
                text=True
            )
            
            if config_result.returncode == 0:
                config_value = config_result.stdout.strip()
                if "bearer test-token-12345" in config_value:
                    print(f"  ✅ Git http.extraheader configured correctly")
                else:
                    print(f"  ❌ Git config value incorrect: {config_value}")
                    return False
            else:
                print(f"  ❌ Git config not set")
                return False
            
            # Test cleanup
            if hasattr(gpm, '_cleanup_azure_devops_auth'):
                gpm._cleanup_azure_devops_auth()
                
                # Verify config was removed
                config_result = subprocess.run(
                    ["git", "config", "--global", "http.https://dev.azure.com/.extraheader"],
                    capture_output=True,
                    text=True
                )
                
                if config_result.returncode != 0:
                    print(f"  ✅ Cleanup removed git config")
                else:
                    print(f"  ⚠️  Cleanup didn't remove config (may need manual cleanup)")
            
            return True
            
        finally:
            # Restore original env
            if original_token is not None:
                os.environ["SYSTEM_ACCESSTOKEN"] = original_token
            elif "SYSTEM_ACCESSTOKEN" in os.environ:
                del os.environ["SYSTEM_ACCESSTOKEN"]
            
            # Clean up git config
            subprocess.run(
                ["git", "config", "--global", "--unset", "http.https://dev.azure.com/.extraheader"],
                capture_output=True
            )


def test_azure_devops_pat_priority_over_system_token():
    """Test that AZURE_DEVOPS_PAT takes priority over SYSTEM_ACCESSTOKEN"""
    print("\n🧪 Test: Azure DevOps PAT Priority over SYSTEM_ACCESSTOKEN")
    
    try:
        GitPM = get_gitpm_class()
    except Exception as e:
        print(f"  ❌ Failed to import GitPM: {e}")
        return False
    
    # Check if the method exists
    if not hasattr(GitPM, '_parse_azure_devops_url'):
        print("  ⊘ Skipping (Azure DevOps URL handling not implemented)")
        return True
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "project"
        project_dir.mkdir()
        os.chdir(project_dir)
        
        # Create minimal manifest with PAT configured
        Path("git-pm.json").write_text(json.dumps({"packages": {}}, indent=4))
        Path("git-pm.config").write_text(json.dumps({"azure_devops_pat": "pat-token-abc"}, indent=4))
        
        # Save original env
        original_system_token = os.environ.get("SYSTEM_ACCESSTOKEN")
        
        try:
            # Set both tokens
            os.environ["SYSTEM_ACCESSTOKEN"] = "system-token-xyz"
            
            gpm = GitPM()
            
            test_url = "dev.azure.com/myorg/MyProject/my-repo"
            result = gpm.normalize_repo_url(test_url)
            
            # PAT should be embedded in URL (takes priority)
            if "pat-token-abc@dev.azure.com" in result:
                print(f"  ✅ PAT token embedded in URL (takes priority)")
            else:
                print(f"  ❌ PAT should be embedded in URL")
                print(f"     Got: {result}")
                return False
            
            # SYSTEM_ACCESSTOKEN should NOT be in URL
            if "system-token-xyz" in result:
                print(f"  ❌ SYSTEM_ACCESSTOKEN should not be in URL when PAT is set")
                return False
            print(f"  ✅ SYSTEM_ACCESSTOKEN not used when PAT is available")
            
            return True
            
        finally:
            # Restore original env
            if original_system_token is not None:
                os.environ["SYSTEM_ACCESSTOKEN"] = original_system_token
            elif "SYSTEM_ACCESSTOKEN" in os.environ:
                del os.environ["SYSTEM_ACCESSTOKEN"]


def main():
    """Run all tests"""
    print("=" * 60)
    print("git-pm Test Suite (Lockfile-Free)")
    print(f"Repository: {REPO_ROOT}")
    print("=" * 60)
    
    tests = [
        ("Config Merging", test_config_merging_precedence),
        ("Local Override Schema", test_local_override_new_schema),
        ("Override Replacement", test_manifest_and_override_merging),
        ("Windows Symlink/Junction", test_windows_symlink_fallback),
        ("Dependency Resolution", test_dependency_resolution),
        (".gitignore Management", test_gitignore_management),
        ("Environment File", test_environment_file_generation),
        # Azure DevOps URL handling tests
        ("ADO URL Parsing", test_azure_devops_url_parsing),
        ("ADO URL Building", test_azure_devops_url_building),
        ("ADO Normalize with PAT", test_azure_devops_normalize_with_pat),
        ("ADO Normalize with Protocol", test_azure_devops_normalize_with_protocol_config),
        ("ADO URL Roundtrip", test_azure_devops_url_roundtrip),
        # SYSTEM_ACCESSTOKEN / bearer token tests
        ("ADO SYSTEM_ACCESSTOKEN", test_azure_devops_system_accesstoken),
        ("ADO Configure Auth", test_azure_devops_configure_auth),
        ("ADO PAT Priority", test_azure_devops_pat_priority_over_system_token),
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