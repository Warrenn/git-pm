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
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

__version__ = "0.1.3"


class SimpleYAML:
    """Simple YAML parser for git-pm's subset of YAML"""
    
    @staticmethod
    def load(file_obj):
        """Load YAML from file object"""
        lines = file_obj.readlines()
        return SimpleYAML._parse_lines(lines)
    
    @staticmethod
    def loads(text):
        """Load YAML from string"""
        lines = text.split('\n')
        return SimpleYAML._parse_lines(lines)
    
    @staticmethod
    def _parse_lines(lines):
        """Parse YAML lines into dictionary"""
        result = {}
        stack = [(result, -1)]
        
        for line_num, line in enumerate(lines, 1):
            line = line.rstrip()
            if not line or line.lstrip().startswith('#'):
                continue
            
            indent = len(line) - len(line.lstrip())
            line = line.lstrip()
            
            if ':' in line:
                key, _, value = line.partition(':')
                key = key.strip()
                value = value.strip()
                
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                while len(stack) > 1 and stack[-1][1] >= indent:
                    stack.pop()
                
                parent_dict = stack[-1][0]
                
                if not value:
                    new_dict = {}
                    parent_dict[key] = new_dict
                    stack.append((new_dict, indent))
                else:
                    parent_dict[key] = value
        
        return result
    
    @staticmethod
    def dump(data, file_obj):
        """Dump data to YAML format"""
        SimpleYAML._dump_dict(data, file_obj, 0)
    
    @staticmethod
    def _dump_dict(data, file_obj, indent):
        """Recursively dump dictionary"""
        for key, value in data.items():
            if isinstance(value, dict):
                file_obj.write("{}{}:\n".format("  " * indent, key))
                SimpleYAML._dump_dict(value, file_obj, indent + 1)
            else:
                file_obj.write("{}{}: {}\n".format("  " * indent, key, value))


class GitPM:
    def __init__(self):
        self.script_dir = Path(__file__).parent.resolve()
        self.manifest_dir = self._find_manifest_dir()
        self.project_root = self.manifest_dir  # Backwards compatibility
        
        self.config = self.load_config()
        self.manifest_file = self.manifest_dir / "git-pm.yaml"
        self.local_override_file = self.manifest_dir / "git-pm.local.yaml"
        self.lockfile = self.manifest_dir / "git-pm.lock"
        self.packages_dir = self.manifest_dir / self.config["packages_dir"]
    
    def _find_manifest_dir(self):
        """Find manifest directory - checks parent first, then script directory"""
        parent_dir = self.script_dir.parent
        if (parent_dir / "git-pm.yaml").exists():
            return parent_dir
        return self.script_dir
    
    def load_config(self):
        """Load configuration with defaults"""
        config = {
            "packages_dir": ".git-packages",
            "cache_dir": str(Path.home() / ".cache" / "git-pm"),
            "git_protocol": {},
            "url_patterns": {}
        }
        
        # Try to load default config from manifest directory first
        default_config_manifest = self.manifest_dir / "git-pm.default.yaml" if hasattr(self, 'manifest_dir') else None
        default_config_script = self.script_dir / "git-pm.default.yaml"
        
        if default_config_manifest and default_config_manifest.exists():
            with open(default_config_manifest, 'r') as f:
                defaults = SimpleYAML.load(f)
                config.update(defaults)
        elif default_config_script.exists():
            with open(default_config_script, 'r') as f:
                defaults = SimpleYAML.load(f)
                config.update(defaults)
        
        # Load user config from manifest directory
        config_file = self.manifest_dir / "git-pm.config.yaml" if hasattr(self, 'manifest_dir') else self.script_dir / "git-pm.config.yaml"
        if config_file.exists():
            with open(config_file, 'r') as f:
                user_config = SimpleYAML.load(f)
                config.update(user_config)
        
        return config
    
    def check_git(self):
        """Check if git is installed"""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            print("✓ Git detected: {}".format(result.stdout.strip()))
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("✗ Git not found. Please install git first.")
            return False
    
    def load_manifest(self):
        """Load package manifest"""
        print("📄 Loading manifest...")
        
        if not self.manifest_file.exists():
            print("Error: git-pm.yaml not found in {}".format(self.manifest_dir))
            print("       (Looked in parent directory first, then script directory)")
            return {}
        
        with open(self.manifest_file, 'r') as f:
            data = SimpleYAML.load(f)
            return data.get("packages", {})
    
    def load_local_overrides(self):
        """Load local development overrides"""
        if not self.local_override_file.exists():
            return {}
        
        print("Applying local overrides from {}".format(self.local_override_file.name))
        with open(self.local_override_file, 'r') as f:
            data = SimpleYAML.load(f)
            return data.get("overrides", {})
    
    def get_cache_key(self, repo, path, ref_type, ref_value):
        """Generate cache key for package"""
        cache_str = "{}:{}:{}:{}".format(repo, path, ref_type, ref_value)
        return hashlib.sha256(cache_str.encode()).hexdigest()[:16]
    
    def normalize_repo_url(self, repo):
        """Convert repository identifier to full URL"""
        repo = repo.strip()
        
        if repo.startswith(("http://", "https://", "git@", "file://")):
            return repo
        
        if "/" not in repo:
            return repo
        
        canonical_repo = repo
        if not canonical_repo.endswith(".git"):
            canonical_repo = repo
        
        if canonical_repo.startswith("http://") or canonical_repo.startswith("https://") or canonical_repo.startswith("file://"):
            return canonical_repo
        
        domain = canonical_repo.split("/")[0]
        path = "/".join(canonical_repo.split("/")[1:])
        
        env_token_key = "GIT_PM_TOKEN_{}".format(domain.replace(".", "_"))
        token = os.getenv(env_token_key)
        
        if token:
            if "github.com" in domain:
                return "https://{}@github.com/{}.git".format(token, path)
            elif "dev.azure.com" in domain or "visualstudio.com" in domain:
                return "https://{}@{}/{}.git".format(token, domain, path)
            else:
                return "https://oauth2:{}@{}/{}.git".format(token, domain, path)
        
        if "url_patterns" in self.config and domain in self.config["url_patterns"]:
            pattern = self.config["url_patterns"][domain]
            return pattern.format(path=path)
        
        protocol = "ssh"
        if "git_protocol" in self.config and domain in self.config["git_protocol"]:
            protocol = self.config["git_protocol"][domain]
        
        if protocol == "ssh" or self._can_use_ssh(domain):
            if "github.com" in domain or "gitlab.com" in domain:
                return "git@{}:{}.git".format(domain, path)
            elif "dev.azure.com" in domain:
                return "git@ssh.dev.azure.com:v3/{}".format(path)
            elif "visualstudio.com" in domain:
                parts = path.split("/")
                if len(parts) >= 2:
                    org = parts[0]
                    return "git@vs-ssh.visualstudio.com:v3/{}/{}".format(org, "/".join(parts[1:]))
        
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
            # Check if repository is already initialized
            git_dir = cache_path / ".git"
            is_initialized = git_dir.exists() and git_dir.is_dir()
            
            if not is_initialized:
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
            else:
                # Already initialized - update remote URL in case it changed
                subprocess.run(
                    ["git", "remote", "set-url", "origin", repo_url],
                    cwd=cache_path,
                    check=True,
                    capture_output=True
                )
            
            # Set sparse checkout pattern (always update in case path changed)
            sparse_file = cache_path / ".git" / "info" / "sparse-checkout"
            sparse_file.parent.mkdir(parents=True, exist_ok=True)
            with open(sparse_file, 'w') as f:
                f.write("{}/*\n".format(path))
            
            # Fetch and checkout
            try:
                if ref_type == "branch":
                    subprocess.run(
                        ["git", "fetch", "--depth=1", "origin", ref_value],
                        cwd=cache_path,
                        check=True,
                        capture_output=True
                    )
                    checkout_ref = "FETCH_HEAD"
                else:
                    subprocess.run(
                        ["git", "fetch", "origin"],
                        cwd=cache_path,
                        check=True,
                        capture_output=True
                    )
                    checkout_ref = ref_value if ref_type == "commit" else "refs/tags/{}".format(ref_value)
            except subprocess.CalledProcessError:
                subprocess.run(
                    ["git", "fetch", "origin"],
                    cwd=cache_path,
                    check=True,
                    capture_output=True
                )
                checkout_ref = ref_value if ref_type == "commit" else ("refs/tags/{}".format(ref_value) if ref_type == "tag" else "FETCH_HEAD")
            
            subprocess.run(
                ["git", "checkout", checkout_ref],
                cwd=cache_path,
                check=True,
                capture_output=True
            )
            
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
            if cache_path.exists():
                shutil.rmtree(cache_path)
            return None
    
    def copy_package(self, cache_path, package_path, dest_path):
        """Copy package from cache to destination"""
        src = cache_path / package_path
        
        if not src.exists():
            print("    ✗ Package path not found in cache: {}".format(package_path))
            return False
        
        if dest_path.exists():
            shutil.rmtree(dest_path)
        
        try:
            shutil.copytree(src, dest_path, symlinks=False, ignore_dangling_symlinks=True)
            print("    ✓ Copied: {} -> {}".format(package_path, dest_path.relative_to(self.manifest_dir)))
            return True
        except Exception as e:
            print("    ✗ Copy failed: {}".format(e))
            return False
    
    def install_package(self, name, config, overrides):
        """Install a single package"""
        print("📦 Installing {}...".format(name))
        
        if name in overrides:
            override = overrides[name]
            if override.get("type") == "local":
                local_path = Path(override["path"])
                if not local_path.is_absolute():
                    local_path = (self.manifest_dir / local_path).resolve()
                
                if not local_path.exists():
                    print("  ✗ Local path does not exist: {}".format(local_path))
                    return None
                
                dest_path = self.packages_dir / name
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                
                shutil.copytree(local_path, dest_path, symlinks=False)
                print("  Override: {} -> local".format(name))
                print("    ✓ Copied from: {}".format(local_path))
                
                return {
                    "type": "local",
                    "path": str(local_path),
                    "installed_at": datetime.now().isoformat()
                }
        
        repo = config.get("repo")
        path = config.get("path", "")
        ref = config.get("ref", {})
        ref_type = ref.get("type", "branch")
        ref_value = ref.get("value", "main")
        
        repo_url = self.normalize_repo_url(repo)
        cache_key = self.get_cache_key(repo, path, ref_type, ref_value)
        cache_path = self.get_cache_path(cache_key)
        
        if cache_path.exists():
            print("  Found in cache: {}".format(cache_key))
        else:
            commit_sha = self.sparse_checkout_package(repo_url, ref_type, ref_value, path, cache_path)
            if not commit_sha:
                return None
        
        dest_path = self.packages_dir / name
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.copy_package(cache_path, path, dest_path):
            return None
        
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cache_path,
            capture_output=True,
            text=True
        )
        commit_sha = result.stdout.strip() if result.returncode == 0 else "unknown"
        
        return {
            "repo": repo,
            "path": path,
            "ref": {"type": ref_type, "value": ref_value},
            "cache_key": cache_key,
            "commit": commit_sha,
            "installed_at": datetime.now().isoformat()
        }
    
    def cmd_install(self):
        """Install all packages"""
        print("🚀 git-pm install")
        
        if not self.check_git():
            return 1
        
        print("📋 Loading configuration...")
        
        packages = self.load_manifest()
        if not packages:
            print("Error: No packages defined in manifest")
            return 1
        
        overrides = self.load_local_overrides()
        
        print("📥 Installing {} package(s)...".format(len(packages)))
        
        self.packages_dir.mkdir(parents=True, exist_ok=True)
        
        lockfile_data = {"packages": {}}
        success_count = 0
        
        for name, config in packages.items():
            result = self.install_package(name, config, overrides)
            if result:
                lockfile_data["packages"][name] = result
                success_count += 1
        
        if success_count > 0:
            print("💾 Saving lockfile...")
            with open(self.lockfile, 'w') as f:
                SimpleYAML.dump(lockfile_data, f)
        
        print("✅ Installation complete!")
        return 0
    
    def cmd_update(self):
        """Update packages"""
        print("🔄 git-pm update")
        
        if not self.check_git():
            return 1
        
        print("📋 Loading configuration...")
        packages = self.load_manifest()
        
        if not packages:
            print("Error: No packages in manifest")
            return 1
        
        print("🔄 Updating packages...")
        
        updated = 0
        for name, config in packages.items():
            ref = config.get("ref", {})
            ref_type = ref.get("type", "branch")
            
            if ref_type == "branch":
                print("📦 Updating {}...".format(name))
                
                repo = config.get("repo")
                path = config.get("path", "")
                ref_value = ref.get("value", "main")
                
                repo_url = self.normalize_repo_url(repo)
                cache_key = self.get_cache_key(repo, path, ref_type, ref_value)
                cache_path = self.get_cache_path(cache_key)
                
                if cache_path.exists():
                    print("  Found in cache: {}".format(cache_key))
                    print("  Updating branch to latest...")
                
                overrides = self.load_local_overrides()
                result = self.install_package(name, config, overrides)
                if result:
                    updated += 1
        
        print("✅ Updated {} package(s)".format(updated))
        return 0
    
    def cmd_clean(self):
        """Remove all installed packages"""
        print("🧹 git-pm clean")
        
        if self.packages_dir.exists():
            shutil.rmtree(self.packages_dir)
            print("✓ Removed {}".format(self.packages_dir))
        
        if self.lockfile.exists():
            self.lockfile.unlink()
            print("✓ Removed lockfile")
        
        print("✅ Clean complete!")
        return 0
    
    def cmd_list(self):
        """List installed packages"""
        print("📦 git-pm list")
        
        if not self.lockfile.exists():
            print("No packages installed (no lockfile found)")
            return 0
        
        with open(self.lockfile, 'r') as f:
            lockfile = SimpleYAML.load(f)
        
        packages = lockfile.get("packages", {})
        if not packages:
            print("No packages in lockfile")
            return 0
        
        print("\nInstalled packages:")
        for name, info in packages.items():
            if info.get("type") == "local":
                print("  {} (local: {})".format(name, info.get("path")))
            else:
                print("  {} - {}@{} [{}]".format(
                    name,
                    info.get("repo"),
                    info.get("ref", {}).get("value"),
                    info.get("commit", "")[:8]
                ))
        
        return 0
    
    def cmd_add(self, name, repo, path, ref_type, ref_value):
        """Add a package to manifest"""
        print("📦 git-pm add")
        
        # For add command, determine where to create the manifest
        # If we're running from the parent directory (project root), use that
        # Otherwise use script directory
        cwd = Path.cwd()
        parent_dir = self.script_dir.parent
        
        if cwd == parent_dir or (parent_dir / "git-pm.yaml").exists():
            # We're in parent directory or parent has manifest
            manifest_dir = parent_dir
        else:
            # Use script directory
            manifest_dir = self.script_dir
        
        manifest_file = manifest_dir / "git-pm.yaml"
        
        if manifest_file.exists():
            with open(manifest_file, 'r') as f:
                manifest = SimpleYAML.load(f)
        else:
            print("Creating new manifest...")
            manifest = {"packages": {}}
        
        if "packages" not in manifest:
            manifest["packages"] = {}
        
        manifest["packages"][name] = {
            "repo": repo,
            "path": path,
            "ref": {
                "type": ref_type,
                "value": ref_value
            }
        }
        
        print("Saving manifest to {}...".format(manifest_file.name))
        with open(manifest_file, 'w') as f:
            SimpleYAML.dump(manifest, f)
        
        print("✓ Package '{}' added to manifest".format(name))
        print("\nPackage configuration:")
        print("  Name: {}".format(name))
        print("  Repo: {}".format(repo))
        print("  Path: {}".format(path))
        print("  Ref:  {}:{}".format(ref_type, ref_value))
        print("\nRun 'python git-pm.py install' to install the package")
        
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="git-pm: Git Package Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--version", action="version", version="git-pm {}".format(__version__))
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    subparsers.add_parser("install", help="Install packages from manifest")
    subparsers.add_parser("update", help="Update packages to latest versions")
    subparsers.add_parser("clean", help="Remove all installed packages")
    subparsers.add_parser("list", help="List installed packages")
    
    add_parser = subparsers.add_parser("add", help="Add or update a package in the manifest")
    add_parser.add_argument("name", help="Package name")
    add_parser.add_argument("repo", help="Repository identifier")
    add_parser.add_argument("--path", default="", help="Path within repository")
    add_parser.add_argument("--ref-type", choices=["tag", "branch", "commit"], default="branch", help="Reference type")
    add_parser.add_argument("--ref-value", default="main", help="Reference value")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    gpm = GitPM()
    
    if args.command == "install":
        return gpm.cmd_install()
    elif args.command == "update":
        return gpm.cmd_update()
    elif args.command == "clean":
        return gpm.cmd_clean()
    elif args.command == "list":
        return gpm.cmd_list()
    elif args.command == "add":
        return gpm.cmd_add(args.name, args.repo, args.path, args.ref_type, args.ref_value)
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
