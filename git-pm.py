#!/usr/bin/env python3
"""
git-pm: Git Package Manager
A package manager that uses git sparse-checkout to manage dependencies from monorepos.
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    # Fallback to json if PyYAML not available
    yaml = None

__version__ = "0.1.0"


class GitPM:
    """Main git-pm class"""
    
    def __init__(self):
        self.system = platform.system()
        self.user_config_dir = self._get_user_config_dir()
        self.user_cache_dir = self._get_user_cache_dir()
        self.project_root = Path.cwd()
        self.config = {}
        self.manifest = {}
        self.lockfile = {}
        
    def _get_user_config_dir(self):
        """Get user-level config directory"""
        if self.system == "Windows":
            base = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
            return Path(base) / "git-pm"
        else:
            return Path.home() / ".git-pm"
    
    def _get_user_cache_dir(self):
        """Get user-level cache directory"""
        if self.system == "Windows":
            base = os.getenv("LOCALAPPDATA", os.path.expanduser("~"))
            return Path(base) / "git-pm" / "cache"
        else:
            xdg_cache = os.getenv("XDG_CACHE_HOME")
            if xdg_cache:
                return Path(xdg_cache) / "git-pm"
            return Path.home() / ".cache" / "git-pm"
    
    def check_git_installed(self):
        """Check if git is installed and print helpful message if not"""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print("✓ Git detected: {}".format(result.stdout.strip()))
                return True
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # Git not found, print helpful instructions
        print("❌ Git is not installed or not in PATH")
        print("")
        if self.system == "Windows":
            print("To install Git on Windows:")
            print("  1. Download from: https://git-scm.com/download/win")
            print("  2. Or use winget: winget install Git.Git")
            print("  3. Or use chocolatey: choco install git")
        elif self.system == "Linux":
            print("To install Git on Linux:")
            print("  Ubuntu/Debian: sudo apt-get install git")
            print("  Fedora/RHEL:   sudo dnf install git")
            print("  Arch:          sudo pacman -S git")
        elif self.system == "Darwin":
            print("To install Git on macOS:")
            print("  1. Install Xcode Command Line Tools: xcode-select --install")
            print("  2. Or use Homebrew: brew install git")
        
        return False
    
    def load_config(self):
        """Load and merge configuration from multiple sources"""
        config = {}
        
        # 1. Load user-level config
        user_config_file = self.user_config_dir / "config.yaml"
        if user_config_file.exists():
            user_config = self._load_yaml_file(user_config_file)
            if user_config:
                config = self._merge_dicts(config, user_config)
                print("  Loaded user config: {}".format(user_config_file))
        
        # 2. Load project-level config
        project_config_file = self.project_root / ".git-pm" / "config.yaml"
        if project_config_file.exists():
            project_config = self._load_yaml_file(project_config_file)
            if project_config:
                config = self._merge_dicts(config, project_config)
                print("  Loaded project config: {}".format(project_config_file))
        
        # 3. Apply defaults
        defaults = {
            "packages_dir": ".git-packages",
            "cache_dir": str(self.user_cache_dir),
            "auto_update_branches": True,
            "parallel_downloads": 4,
            "git_protocol": {},
            "url_patterns": {},
            "credentials": {}
        }
        config = self._merge_dicts(defaults, config)
        
        self.config = config
        return config
    
    def _merge_dicts(self, base, override):
        """Recursively merge two dictionaries"""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_dicts(result[key], value)
            else:
                result[key] = value
        return result
    
    def _load_yaml_file(self, filepath):
        """Load YAML file, with fallback to JSON"""
        try:
            with open(filepath, 'r') as f:
                if yaml:
                    return yaml.safe_load(f)
                else:
                    # Try JSON as fallback
                    print("Note: PyYAML not installed. Trying to parse as JSON...")
                    print("      For better YAML support: pip install PyYAML")
                    try:
                        return json.load(f)
                    except json.JSONDecodeError as je:
                        print("")
                        print("Error: File appears to be YAML, not JSON")
                        print("       Please install PyYAML: pip install PyYAML")
                        print("       Or convert your file to JSON format")
                        return None
        except Exception as e:
            print("Warning: Failed to load {}: {}".format(filepath, e))
            return None
    
    def _save_yaml_file(self, filepath, data):
        """Save data to YAML file, with fallback to JSON"""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(filepath, 'w') as f:
                if yaml:
                    yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
                else:
                    json.dump(data, f, indent=2)
        except Exception as e:
            print("Error: Failed to save {}: {}".format(filepath, e))
            return False
        return True
    
    def load_manifest(self):
        """Load manifest with local overrides"""
        manifest_file = self.project_root / "git-pm.yaml"
        
        if not manifest_file.exists():
            print("Error: git-pm.yaml not found in current directory")
            return None
        
        manifest = self._load_yaml_file(manifest_file)
        if not manifest:
            return None
        
        # Load local overrides
        local_override_file = self.project_root / "git-pm.local.yaml"
        if local_override_file.exists():
            overrides = self._load_yaml_file(local_override_file)
            if overrides and "overrides" in overrides:
                print("  Applying local overrides from git-pm.local.yaml")
                manifest = self._apply_overrides(manifest, overrides["overrides"])
        
        self.manifest = manifest
        return manifest
    
    def _apply_overrides(self, manifest, overrides):
        """Apply local overrides to manifest"""
        if "packages" not in manifest:
            return manifest
        
        for pkg_name, override_config in overrides.items():
            if pkg_name in manifest["packages"]:
                # Replace package config with override
                manifest["packages"][pkg_name] = override_config
                print("    Override: {} -> local".format(pkg_name))
        
        return manifest
    
    def generate_cache_key(self, repo, ref_type, ref_value, path):
        """Generate hash-based cache key"""
        canonical = "{}#{}:{}#{}".format(repo, ref_type, ref_value, path)
        hash_obj = hashlib.sha256(canonical.encode())
        return hash_obj.hexdigest()[:16]
    
    def resolve_git_url(self, canonical_repo):
        """Resolve canonical repo identifier to actual git URL"""
        # Handle file:// URLs directly (for testing)
        if canonical_repo.startswith("file://"):
            # Convert relative file:// paths to absolute paths
            # This is important because git operations run from different working directories
            file_path = canonical_repo[7:]  # Remove 'file://' prefix
            
            # If it's a relative path, convert to absolute
            if not file_path.startswith('/'):
                # Get absolute path relative to project root
                abs_path = (self.project_root / file_path).resolve()
                return "file://{}".format(abs_path)
            
            return canonical_repo
        
        domain = canonical_repo.split("/")[0]
        path = "/".join(canonical_repo.split("/")[1:])
        
        # Check for token in environment
        env_token_key = "GIT_PM_TOKEN_{}".format(domain.replace(".", "_"))
        token = os.getenv(env_token_key)
        
        if token:
            # Use HTTPS with token
            if "github.com" in domain:
                return "https://{}@github.com/{}.git".format(token, path)
            elif "dev.azure.com" in domain or "visualstudio.com" in domain:
                return "https://{}@{}/{}.git".format(token, domain, path)
            else:
                return "https://oauth2:{}@{}/{}.git".format(token, domain, path)
        
        # Check user config for URL patterns
        if "url_patterns" in self.config and domain in self.config["url_patterns"]:
            pattern = self.config["url_patterns"][domain]
            return pattern.format(path=path)
        
        # Check git protocol preference
        protocol = "ssh"
        if "git_protocol" in self.config and domain in self.config["git_protocol"]:
            protocol = self.config["git_protocol"][domain]
        
        # Try to detect SSH availability
        if protocol == "ssh" or self._can_use_ssh(domain):
            if "github.com" in domain or "gitlab.com" in domain:
                return "git@{}:{}.git".format(domain, path)
        
        # Fallback to HTTPS
        return "https://{}/{}.git".format(domain, path)
    
    def _can_use_ssh(self, domain):
        """Test if SSH works for this domain"""
        try:
            git_host = "git@{}".format(domain)
            result = subprocess.run(
                ["ssh", "-T", "-o", "StrictHostKeyChecking=no", 
                 "-o", "ConnectTimeout=3", git_host],
                capture_output=True,
                timeout=5
            )
            # GitHub/GitLab return 1 but with success message
            return result.returncode in [0, 1]
        except:
            return False
    
    def get_cache_path(self, cache_key):
        """Get path to cached package"""
        cache_dir = Path(self.config["cache_dir"])
        return cache_dir / "objects" / cache_key
    
    def sparse_checkout_package(self, repo_url, ref_type, ref_value, path, cache_path):
        """Clone and sparse checkout a specific path from repo"""
        print("  Cloning {} ({}:{})...".format(repo_url, ref_type, ref_value))
        
        cache_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Initialize repository
            subprocess.run(
                ["git", "init"],
                cwd=cache_path,
                check=True,
                capture_output=True
            )
            
            # Add remote
            subprocess.run(
                ["git", "remote", "add", "origin", repo_url],
                cwd=cache_path,
                check=True,
                capture_output=True
            )
            
            # Configure sparse checkout
            subprocess.run(
                ["git", "config", "core.sparseCheckout", "true"],
                cwd=cache_path,
                check=True,
                capture_output=True
            )
            
            # Set sparse checkout pattern
            sparse_file = cache_path / ".git" / "info" / "sparse-checkout"
            sparse_file.parent.mkdir(parents=True, exist_ok=True)
            with open(sparse_file, 'w') as f:
                f.write("{}/*\n".format(path))
            
            # Simple fetch approach - fetch origin then checkout
            # For file:// URLs and tags, full fetch works best
            try:
                if ref_type == "branch":
                    # Branch: fetch specific branch
                    subprocess.run(
                        ["git", "fetch", "--depth=1", "origin", ref_value],
                        cwd=cache_path,
                        check=True,
                        capture_output=True
                    )
                    checkout_ref = "FETCH_HEAD"
                else:
                    # Tag or commit: fetch everything (more reliable)
                    subprocess.run(
                        ["git", "fetch", "origin"],
                        cwd=cache_path,
                        check=True,
                        capture_output=True
                    )
                    checkout_ref = ref_value if ref_type == "commit" else "refs/tags/{}".format(ref_value)
            except subprocess.CalledProcessError:
                # Fallback: try full fetch
                subprocess.run(
                    ["git", "fetch", "origin"],
                    cwd=cache_path,
                    check=True,
                    capture_output=True
                )
                checkout_ref = ref_value if ref_type == "commit" else ("refs/tags/{}".format(ref_value) if ref_type == "tag" else "FETCH_HEAD")
            
            # Checkout
            subprocess.run(
                ["git", "checkout", checkout_ref],
                cwd=cache_path,
                check=True,
                capture_output=True
            )
            
            # Get actual commit SHA
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=cache_path,
                capture_output=True,
                text=True,
                check=True
            )
            commit_sha = result.stdout.strip()
            
            print("    ✓ Cached at commit: {}".format(commit_sha[:8]))
            return commit_sha
            
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            print("    ✗ Failed to clone: {}".format(error_msg.strip() if error_msg else e))
            # Clean up failed cache
            if cache_path.exists():
                shutil.rmtree(cache_path)
            return None
    
    def create_symlink(self, source, target):
        """Create symlink or junction, cross-platform"""
        target = Path(target)
        source = Path(source).resolve()
        
        # Remove existing link/directory
        if target.exists() or target.is_symlink():
            if target.is_symlink():
                target.unlink()
            elif target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
        
        target.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if self.system == "Windows":
                # Try symlink first, fall back to junction
                try:
                    if source.is_dir():
                        os.symlink(source, target, target_is_directory=True)
                    else:
                        os.symlink(source, target)
                    print("    ✓ Symlink: {} -> {}".format(target.name, source))
                except OSError:
                    # Fall back to junction for directories on Windows
                    if source.is_dir():
                        subprocess.run(
                            ["mklink", "/J", str(target), str(source)],
                            shell=True,
                            check=True,
                            capture_output=True
                        )
                        print("    ✓ Junction: {} -> {}".format(target.name, source))
                    else:
                        raise
            else:
                # Linux/macOS
                os.symlink(source, target)
                print("    ✓ Symlink: {} -> {}".format(target.name, source))
            return True
        except Exception as e:
            print("    ✗ Failed to create link: {}".format(e))
            return False
    
    def install_package(self, pkg_name, pkg_config):
        """Install a single package"""
        print("\n📦 Installing {}...".format(pkg_name))
        
        # Check if local package
        if pkg_config.get("type") == "local":
            local_path = Path(pkg_config["path"]).resolve()
            if not local_path.exists():
                print("  ✗ Local path does not exist: {}".format(local_path))
                return None
            
            print("  Using local path: {}".format(local_path))
            packages_dir = self.project_root / self.config["packages_dir"]
            target = packages_dir / pkg_name
            
            self.create_symlink(local_path, target)
            
            return {
                "type": "local",
                "path": str(local_path),
                "cached_at": datetime.utcnow().isoformat()
            }
        
        # Git package
        repo = pkg_config.get("repo")
        path = pkg_config.get("path", "")
        ref = pkg_config.get("ref", {})
        ref_type = ref.get("type", "branch")
        ref_value = ref.get("value", "main")
        
        if not repo:
            print("  ✗ Missing 'repo' in package config")
            return None
        
        # Generate cache key
        cache_key = self.generate_cache_key(repo, ref_type, ref_value, path)
        cache_path = self.get_cache_path(cache_key)
        
        # Check if already cached
        commit_sha = None
        should_fetch = False
        
        if cache_path.exists():
            print("  Found in cache: {}".format(cache_key))
            
            # For branches, check if we should update
            if ref_type == "branch" and self.config.get("auto_update_branches", True):
                print("  Updating branch to latest...")
                should_fetch = True
        else:
            should_fetch = True
        
        if should_fetch:
            # Resolve git URL
            git_url = self.resolve_git_url(repo)
            
            # Clone with sparse checkout
            commit_sha = self.sparse_checkout_package(
                git_url, ref_type, ref_value, path, cache_path
            )
            
            if not commit_sha:
                return None
        else:
            # Get commit from existing cache
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=cache_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                commit_sha = result.stdout.strip()
            except:
                commit_sha = "unknown"
        
        # Create symlink to package
        packages_dir = self.project_root / self.config["packages_dir"]
        target = packages_dir / pkg_name
        source = cache_path / path
        
        if not source.exists():
            print("  ✗ Path '{}' not found in repository".format(path))
            return None
        
        self.create_symlink(source, target)
        
        return {
            "repo": repo,
            "path": path,
            "ref": ref,
            "resolved_commit": commit_sha,
            "cache_key": cache_key,
            "cached_at": datetime.utcnow().isoformat()
        }
    
    def cmd_install(self, args):
        """Install command"""
        print("🚀 git-pm install")
        print("")
        
        # Check git
        if not self.check_git_installed():
            return 1
        
        print("")
        print("📋 Loading configuration...")
        self.load_config()
        
        print("")
        print("📄 Loading manifest...")
        manifest = self.load_manifest()
        if not manifest or "packages" not in manifest:
            print("Error: No packages defined in manifest")
            return 1
        
        print("")
        print("📥 Installing {} package(s)...".format(len(manifest["packages"])))
        
        # Install packages
        lockfile_data = {
            "version": "1",
            "generated_at": datetime.datetime.now(datetime.UTC),
            "packages": {}
        }
        
        for pkg_name, pkg_config in manifest["packages"].items():
            result = self.install_package(pkg_name, pkg_config)
            if result:
                lockfile_data["packages"][pkg_name] = result
        
        # Save lockfile
        lockfile_path = self.project_root / "git-pm.lock"
        print("")
        print("💾 Saving lockfile...")
        if self._save_yaml_file(lockfile_path, lockfile_data):
            print("  ✓ Lockfile saved: git-pm.lock")
        
        print("")
        print("✅ Installation complete!")
        return 0
    
    def cmd_update(self, args):
        """Update command - refresh branches to latest"""
        print("🔄 git-pm update")
        print("")
        
        if not self.check_git_installed():
            return 1
        
        print("")
        print("📋 Loading configuration...")
        self.load_config()
        
        print("")
        print("📄 Loading manifest...")
        manifest = self.load_manifest()
        if not manifest or "packages" not in manifest:
            print("Error: No packages defined in manifest")
            return 1
        
        print("")
        print("🔄 Updating packages...")
        
        # Force update for branch references
        original_setting = self.config.get("auto_update_branches")
        self.config["auto_update_branches"] = True
        
        updated_count = 0
        for pkg_name, pkg_config in manifest["packages"].items():
            ref = pkg_config.get("ref", {})
            if ref.get("type") == "branch":
                print("\n📦 Updating {}...".format(pkg_name))
                result = self.install_package(pkg_name, pkg_config)
                if result:
                    updated_count += 1
            else:
                print("\n📦 Skipping {} ({}:{} - immutable)".format(
                    pkg_name, ref.get("type"), ref.get("value")
                ))
        
        self.config["auto_update_branches"] = original_setting
        
        print("")
        print("✅ Updated {} package(s)".format(updated_count))
        return 0
    
    def cmd_clean(self, args):
        """Clean command - remove installed packages"""
        print("🧹 git-pm clean")
        print("")
        
        packages_dir = self.project_root / self.config.get("packages_dir", ".git-packages")
        
        if not packages_dir.exists():
            print("Nothing to clean - {} does not exist".format(packages_dir))
            return 0
        
        print("Removing {}...".format(packages_dir))
        try:
            shutil.rmtree(packages_dir)
            print("✅ Cleaned successfully")
        except Exception as e:
            print("Error: Failed to remove {}: {}".format(packages_dir, e))
            return 1
        
        if args.cache:
            cache_dir = Path(self.config.get("cache_dir", self.user_cache_dir))
            if cache_dir.exists():
                print("")
                print("Removing cache at {}...".format(cache_dir))
                try:
                    shutil.rmtree(cache_dir)
                    print("✅ Cache cleaned successfully")
                except Exception as e:
                    print("Error: Failed to remove cache: {}".format(e))
                    return 1
        
        return 0
    
    def cmd_list(self, args):
        """List command - show installed packages"""
        print("📋 git-pm list")
        print("")
        
        self.load_config()
        
        # Check if lockfile exists
        lockfile_path = self.project_root / "git-pm.lock"
        if not lockfile_path.exists():
            print("No packages installed (git-pm.lock not found)")
            print("Run: python git-pm.py install")
            return 0
        
        lockfile = self._load_yaml_file(lockfile_path)
        if not lockfile or "packages" not in lockfile:
            print("No packages in lockfile")
            return 0
        
        packages_dir = self.project_root / self.config["packages_dir"]
        
        print("Installed packages in {}:\n".format(packages_dir))
        
        for pkg_name, pkg_info in lockfile["packages"].items():
            # Check if link exists
            pkg_path = packages_dir / pkg_name
            exists = "✓" if pkg_path.exists() else "✗"
            
            if pkg_info.get("type") == "local":
                print("  {} {} (local)".format(exists, pkg_name))
                print("      Path: {}".format(pkg_info.get("path")))
            else:
                ref = pkg_info.get("ref", {})
                ref_type = ref.get("type", "branch")
                ref_value = ref.get("value", "unknown")
                commit = pkg_info.get("resolved_commit", "unknown")[:8]
                
                print("  {} {} ({}:{})".format(exists, pkg_name, ref_type, ref_value))
                print("      Repo: {}".format(pkg_info.get("repo")))
                print("      Path: {}".format(pkg_info.get("path")))
                print("      Commit: {}".format(commit))
            
            print("")
        
        return 0


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="git-pm: Git-based package manager using sparse-checkout"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="git-pm {}".format(__version__)
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Install command
    install_parser = subparsers.add_parser(
        "install",
        help="Install packages from manifest"
    )
    
    # Update command
    update_parser = subparsers.add_parser(
        "update",
        help="Update packages (refresh branches to latest)"
    )
    
    # Clean command
    clean_parser = subparsers.add_parser(
        "clean",
        help="Remove installed packages"
    )
    clean_parser.add_argument(
        "--cache",
        action="store_true",
        help="Also remove cache directory"
    )
    
    # List command
    list_parser = subparsers.add_parser(
        "list",
        help="List installed packages"
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Create git-pm instance
    gpm = GitPM()
    
    # Route to command
    if args.command == "install":
        return gpm.cmd_install(args)
    elif args.command == "update":
        return gpm.cmd_update(args)
    elif args.command == "clean":
        return gpm.cmd_clean(args)
    elif args.command == "list":
        return gpm.cmd_list(args)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())