#!/usr/bin/env python3
"""
git-pm: Git Package Manager
A package manager that uses git sparse-checkout to manage dependencies with full dependency resolution.

Version 0.2.9 - Full dependency resolution with explicit versions
Requires Python 3.8+ (3.7 may work but is not tested)
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

# Fix Windows encoding issues with Unicode characters (emojis)
if sys.platform == 'win32':
    # Set UTF-8 encoding for stdout and stderr
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

__version__ = "0.2.9"


class GitPM:
    def __init__(self):
        # Find project root by looking for git-pm.json
        self.project_root = self._find_project_root()
        
        self.config = self.load_config()
        self.manifest_file = self.project_root / "git-pm.json"
        self.local_override_file = self.project_root / "git-pm.local"
        self.lockfile = self.project_root / "git-pm.lock"
        self.packages_dir = self.project_root / self.config["packages_dir"]
        
        # Dependency resolution state
        self.discovered = {}  # All discovered packages
        self.branch_commits = {}  # Resolved branch -> commit mappings
    
    def _find_project_root(self):
        """Find project root by looking for git-pm.json"""
        current = Path.cwd()
        
        # Check current directory first
        if (current / "git-pm.json").exists():
            return current
        
        # Check parent directories
        for parent in current.parents:
            if (parent / "git-pm.json").exists():
                return parent
        
        # No manifest found, use current directory
        return current
    
    def _load_json_file(self, file_path, description="config file"):
        """Load and parse a JSON file with helpful error messages"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print("Error: Invalid JSON in {} (line {}, column {})".format(
                file_path.name, e.lineno, e.colno))
            print("  {}".format(str(e.msg)))
            raise
        except Exception as e:
            print("Error: Failed to load {}: {}".format(description, e))
            raise
    
    def load_config(self):
        """Load configuration with three-way merge: defaults < user < project"""
        # 1. Start with defaults
        config = {
            "packages_dir": ".git-packages",
            "cache_dir": str(Path.home() / ".cache" / "git-pm"),
            "git_protocol": {},
            "url_patterns": {},
            "azure_devops_pat": os.getenv("AZURE_DEVOPS_PAT", "")
        }
        
        # 2. Apply user config (overrides defaults)
        user_config = self.load_user_config()
        if user_config:
            config = self._deep_merge(config, user_config)
        
        # 3. Apply project config (overrides user and defaults)
        project_config = self.load_project_config()
        if project_config:
            config = self._deep_merge(config, project_config)
        
        return config
    
    def _deep_merge(self, base, override):
        """
        Deep merge two dictionaries.
        Override values take precedence over base values.
        Nested dicts are merged recursively.
        
        Args:
            base: Base dictionary
            override: Override dictionary (wins on conflict)
        
        Returns:
            Merged dictionary
        """
        merged = dict(base)
        
        for key, value in override.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                # Recursively merge nested dicts
                merged[key] = self._deep_merge(merged[key], value)
            else:
                # Override completely
                merged[key] = value
        
        return merged
    
    def get_user_config_path(self):
        """Get user-level configuration file path (cross-platform)"""
        return Path.home() / '.git-pm' / 'config'
    
    def load_user_config(self):
        """Load user-level configuration from ~/.git-pm/config"""
        config_path = self.get_user_config_path()
        
        if not config_path.exists():
            return {}
        
        try:
            return self._load_json_file(config_path, "user config")
        except Exception:
            return {}
    
    def load_project_config(self):
        """Load project-level configuration from git-pm.config"""
        config_path = self.project_root / 'git-pm.config'
        
        if not config_path.exists():
            return {}
        
        try:
            return self._load_json_file(config_path, "project config")
        except Exception:
            return {}

    
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
            print("Error: git-pm.json not found in {}".format(self.project_root))
            return {}
        
        data = self._load_json_file(self.manifest_file, "manifest")
        return data.get("packages", {})
    
    def load_local_overrides(self):
        """Load local development overrides (same schema as manifest)"""
        if not self.local_override_file.exists():
            return {}
        
        print("Applying local overrides from {}".format(self.local_override_file.name))
        data = self._load_json_file(self.local_override_file, "local overrides")
        return data.get("packages", {})
    
    def get_cache_key(self, repo, path, ref_type, ref_value):
        """Generate cache key for package"""
        cache_str = "{}:{}:{}:{}".format(repo, path, ref_type, ref_value)
        return hashlib.sha256(cache_str.encode()).hexdigest()[:16]
    
    def is_local_package(self, repo_url):
        """Check if a repository URL is a local file path"""
        return repo_url.startswith("file://")
    
    def normalize_repo_url(self, repo):
        """Convert repository identifier to full URL"""
        repo = repo.strip()
        
        # Already a file:// URL
        if repo.startswith("file://"):
            path = repo[7:]  # Remove "file://"
            if not os.path.isabs(path):
                # Make relative paths absolute relative to project root
                path = str((self.project_root / path).resolve())
            return "file://{}".format(path)
        
        # Check if it looks like a local path (starts with ./ ../ / ~)
        if repo.startswith(("./", "../", "/", "~/")):
            if repo.startswith("~/"):
                path = os.path.expanduser(repo)
            elif os.path.isabs(repo):
                path = repo
            else:
                # Relative path - resolve relative to project root
                path = str((self.project_root / repo).resolve())
            return "file://{}".format(path)
        
        # Already a full URL (http/https/git@)
        if repo.startswith(("http://", "https://", "git@")):
            return repo
        
        if "/" not in repo:
            return repo
        
        canonical_repo = repo
        domain = canonical_repo.split("/")[0]
        path = "/".join(canonical_repo.split("/")[1:])
        
        # Check for Azure DevOps PAT from environment
        if self.config.get("azure_devops_pat") and ("dev.azure.com" in domain or "visualstudio.com" in domain):
            token = self.config["azure_devops_pat"]
            return "https://{}@{}/{}.git".format(token, domain, path)
        
        # Check for generic token in environment
        env_token_key = "GIT_PM_TOKEN_{}".format(domain.replace(".", "_"))
        token = os.getenv(env_token_key)
        
        if token:
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
            elif "dev.azure.com" in domain:
                return "git@ssh.dev.azure.com:v3/{}".format(path)
            elif "visualstudio.com" in domain:
                parts = path.split("/")
                if len(parts) >= 2:
                    org = parts[0]
                    return "git@vs-ssh.visualstudio.com:v3/{}/{}".format(org, "/".join(parts[1:]))
        
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
            return result.returncode in [0, 1]
        except:
            return False
    
    def get_cache_path(self, cache_key):
        """Get path to cached package"""
        cache_dir = Path(self.config["cache_dir"])
        return cache_dir / "objects" / cache_key
    
    def resolve_branch_to_commit(self, repo_url, branch_name):
        """Resolve branch to latest commit SHA"""
        cache_key = "{}:{}".format(repo_url, branch_name)
        
        # Check if we've already resolved this branch in this run
        if cache_key in self.branch_commits:
            return self.branch_commits[cache_key]
        
        print("  Resolving branch '{}' to commit...".format(branch_name))
        
        try:
            # Get latest commit for branch
            result = subprocess.run(
                ["git", "ls-remote", repo_url, "refs/heads/{}".format(branch_name)],
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stdout.strip():
                commit_sha = result.stdout.split()[0]
                self.branch_commits[cache_key] = commit_sha
                print("    ✓ Branch '{}' -> {}".format(branch_name, commit_sha[:8]))
                return commit_sha
            else:
                print("    ✗ Branch '{}' not found".format(branch_name))
                return None
        except subprocess.CalledProcessError as e:
            print("    ✗ Failed to resolve branch: {}".format(e))
            return None
    
    def sparse_checkout_package(self, repo_url, ref_type, ref_value, path, cache_path):
        """Clone and sparse checkout a specific path from repo"""
        print("  Cloning {} ({}:{})...".format(repo_url, ref_type, ref_value))
        
        cache_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Check if repository is already initialized
            git_dir = cache_path / ".git"
            is_initialized = git_dir.exists() and git_dir.is_dir()
            
            if not is_initialized:
                subprocess.run(
                    ["git", "init"],
                    cwd=cache_path,
                    check=True,
                    capture_output=True
                )
                
                subprocess.run(
                    ["git", "remote", "add", "origin", repo_url],
                    cwd=cache_path,
                    check=True,
                    capture_output=True
                )
                
                subprocess.run(
                    ["git", "config", "core.sparseCheckout", "true"],
                    cwd=cache_path,
                    check=True,
                    capture_output=True
                )
            else:
                subprocess.run(
                    ["git", "remote", "set-url", "origin", repo_url],
                    cwd=cache_path,
                    check=True,
                    capture_output=True
                )
            
            # Set sparse checkout pattern
            sparse_file = cache_path / ".git" / "info" / "sparse-checkout"
            sparse_file.parent.mkdir(parents=True, exist_ok=True)
            with open(sparse_file, 'w') as f:
                f.write("{}/*\n".format(path) if path else "/*\n")
            
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
            if cache_path.exists():
                shutil.rmtree(cache_path)
            return None
    
    def copy_or_link_package(self, cache_path, package_path, dest_path, use_symlink=False):
        """Copy or symlink package from cache/local to destination"""
        src = cache_path / package_path if package_path else cache_path
        
        if not src.exists():
            print("    ✗ Package path not found: {}".format(src))
            return False
        
        if dest_path.exists():
            # Remove existing (file, dir, or symlink)
            if dest_path.is_symlink() or dest_path.is_file():
                dest_path.unlink()
            else:
                shutil.rmtree(dest_path)
        
        try:
            if use_symlink:
                # Create symlink
                dest_path.symlink_to(src, target_is_directory=True)
                print("    ✓ Linked: {} -> {}".format(src, dest_path.relative_to(self.project_root)))
            else:
                # Copy files
                shutil.copytree(src, dest_path, symlinks=False, ignore_dangling_symlinks=True)
                print("    ✓ Copied: {} -> {}".format(package_path or "root", dest_path.relative_to(self.project_root)))
            return True
        except Exception as e:
            print("    ✗ Operation failed: {}".format(e))
            return False
    
    def _discover_nested_deps(self, pkg_manifest_path, depth, parent_chain, name, local_overrides):
        """Discover nested dependencies from a package's manifest."""
        if not pkg_manifest_path.exists():
            return {}
        
        pkg_data = self._load_json_file(pkg_manifest_path, "package manifest")
        nested_deps = pkg_data.get("packages", {})
        
        # Defensive: ensure nested_deps is a dict
        if not isinstance(nested_deps, dict):
            print("{}  ⚠️  Warning: packages field is not a dictionary, treating as empty".format("  " * depth))
            return {}
        
        if nested_deps:
            print("{}  Found {} dependencies".format("  " * depth, len(nested_deps)))
            # Recursively discover
            discovered_nested = self.discover_dependencies(
                nested_deps,
                depth + 1,
                parent_chain + [name],
                local_overrides
            )
            # Update global discovered dict
            for dep_name, dep_info in discovered_nested.items():
                if dep_name not in self.discovered:
                    self.discovered[dep_name] = dep_info
        
        return nested_deps
    
    def discover_dependencies(self, packages, depth=0, parent_chain=None, local_overrides=None):
        """Recursively discover all dependencies"""
        if parent_chain is None:
            parent_chain = []
        
        if local_overrides is None:
            local_overrides = {}
        
        # Type check
        if not isinstance(packages, dict):
            print("  ✗ Error: packages must be a dictionary, got {}".format(type(packages).__name__))
            return {}
        
        all_discovered = {}
        
        for name, config in packages.items():
            if name in parent_chain:
                print("  ✗ Circular dependency: {}".format(" -> ".join(parent_chain + [name])))
                continue
            
            # Skip if already discovered
            if name in self.discovered:
                continue
            
            print("{}📦 Discovering {}{}...".format(
                "  " * depth,
                name,
                " (depth {})".format(depth) if depth > 0 else ""
            ))
            
            # Check if this package has a local override
            if name in local_overrides:
                config = local_overrides[name]  # Complete replacement
                print("{}  Using local override".format("  " * depth))
            
            # Get repository URL
            repo = config.get("repo")
            if not repo:
                print("{}  ✗ No repository specified".format("  " * depth))
                continue
            
            repo_url = self.normalize_repo_url(repo)
            
            # Check if this is a local package
            if self.is_local_package(repo_url):
                local_path = Path(repo_url[7:])  # Remove file://
                
                if not local_path.exists():
                    print("{}  ✗ Local path does not exist: {}".format("  " * depth, local_path))
                    continue
                
                print("{}  Local package: {}".format("  " * depth, local_path))
                
                # Look for git-pm.json and discover nested dependencies
                path_in_repo = config.get("path", "")
                pkg_manifest_path = local_path / path_in_repo / "git-pm.json" if path_in_repo else local_path / "git-pm.json"
                nested_deps = self._discover_nested_deps(pkg_manifest_path, depth, parent_chain, name, local_overrides)
                
                # Store discovered package
                pkg_info = self._prepare_local_package(name, local_path, config, path_in_repo)
                pkg_info["dependencies"] = nested_deps
                pkg_info["depth"] = depth
                self.discovered[name] = pkg_info
                all_discovered[name] = pkg_info
                continue
            
            # Remote package handling
            path = config.get("path", "")
            ref = config.get("ref", {})
            ref_type = ref.get("type", "branch")
            ref_value = ref.get("value", "main")
            
            # Resolve branch to commit if needed
            if ref_type == "branch":
                commit_sha = self.resolve_branch_to_commit(repo_url, ref_value)
                if commit_sha:
                    config = dict(config)
                    config["ref"] = {"type": "commit", "value": commit_sha}
                    config["original_ref"] = {"type": "branch", "value": ref_value}
                    ref_type = "commit"
                    ref_value = commit_sha
            
            cache_key = self.get_cache_key(repo, path, ref_type, ref_value)
            cache_path = self.get_cache_path(cache_key)
            
            # Clone if not cached or if branch (always pull latest)
            needs_clone = not cache_path.exists() or config.get("original_ref", {}).get("type") == "branch"
            
            if needs_clone:
                commit_sha = self.sparse_checkout_package(repo_url, ref_type, ref_value, path, cache_path)
                if not commit_sha:
                    continue
            else:
                print("  Found in cache: {}".format(cache_key))
            
            # Look for git-pm.json and discover nested dependencies
            pkg_manifest_path = cache_path / path / "git-pm.json" if path else cache_path / "git-pm.json"
            nested_deps = self._discover_nested_deps(pkg_manifest_path, depth, parent_chain, name, local_overrides)
            
            # Store discovered package
            pkg_info = self._prepare_remote_package(name, config, cache_key, cache_path)
            pkg_info["dependencies"] = nested_deps
            pkg_info["depth"] = depth
            self.discovered[name] = pkg_info
            all_discovered[name] = pkg_info
        
        return all_discovered
    
    def topological_sort(self):
        """Sort packages by dependencies (dependencies first)"""
        visited = set()
        temp_mark = set()
        order = []
        
        def visit(pkg_name):
            if pkg_name in temp_mark:
                raise Exception("Circular dependency detected: {}".format(pkg_name))
            if pkg_name in visited:
                return
            
            temp_mark.add(pkg_name)
            
            # Visit dependencies first
            pkg_info = self.discovered.get(pkg_name, {})
            for dep_name in pkg_info.get("dependencies", {}).keys():
                if dep_name in self.discovered:
                    visit(dep_name)
            
            temp_mark.remove(pkg_name)
            visited.add(pkg_name)
            order.append(pkg_name)
        
        for pkg_name in self.discovered.keys():
            if pkg_name not in visited:
                visit(pkg_name)
        
        return order
    
    def install_package(self, name, pkg_info):
        """Install a single package"""
        print("📦 Installing {}...".format(name))
        
        config = pkg_info["config"]
        is_local = pkg_info.get("local", False)
        
        dest_path = self.packages_dir / name
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Handle local package
        if is_local:
            local_path = Path(pkg_info["local_path"])
            path_in_repo = pkg_info.get("path_in_repo", "")
            
            if not local_path.exists():
                print("  ✗ Local path does not exist: {}".format(local_path))
                return None
            
            # Determine source path
            src_path = local_path / path_in_repo if path_in_repo else local_path
            
            # Use symlink for local packages
            if self.copy_or_link_package(src_path.parent if path_in_repo else local_path, 
                                         src_path.name if path_in_repo else "",
                                         dest_path, use_symlink=True):
                print("  Local: {} (symlinked)".format(name))
                return {
                    "type": "local",
                    "repo": config.get("repo"),
                    "path": str(local_path),
                    "symlinked": True,
                    "installed_at": datetime.now().isoformat()
                }
            return None
        
        # Handle remote package
        cache_path = pkg_info.get("cache_path")
        if not cache_path:
            print("  ✗ No cache path available for package")
            return None
        
        path = config.get("path", "")
        
        if not self.copy_or_link_package(cache_path, path, dest_path, use_symlink=False):
            return None
        
        # Get commit SHA
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=cache_path,
            capture_output=True,
            text=True
        )
        commit_sha = result.stdout.strip() if result.returncode == 0 else "unknown"
        
        return {
            "repo": config.get("repo"),
            "path": path,
            "ref": config.get("ref"),
            "original_ref": config.get("original_ref"),
            "cache_key": pkg_info["cache_key"],
            "commit": commit_sha,
            "dependencies": list(pkg_info.get("dependencies", {}).keys()),
            "installed_at": datetime.now().isoformat()
        }
    
    def _prepare_local_package(self, name, local_path, config, path_in_repo=""):
        """Prepare a local package for installation"""
        return {
            "config": config,
            "dependencies": {},
            "depth": 0,
            "local": True,
            "local_path": str(local_path),
            "path_in_repo": path_in_repo
        }
    
    def _prepare_remote_package(self, name, config, cache_key, cache_path):
        """Prepare a remote package for installation"""
        return {
            "config": config,
            "dependencies": {},
            "depth": 0,
            "cache_key": cache_key,
            "cache_path": cache_path
        }
    
    def _setup_package_for_install(self, name, config):
        """
        Set up a package in self.discovered for installation.
        Handles both local and remote packages.
        
        Returns:
            bool: True if successful, False otherwise
        """
        repo = config.get("repo")
        repo_url = self.normalize_repo_url(repo)
        
        # Handle local packages
        if self.is_local_package(repo_url):
            local_path = Path(repo_url[7:])  # Remove file://
            path_in_repo = config.get("path", "")
            self.discovered[name] = self._prepare_local_package(
                name, local_path, config, path_in_repo
            )
            return True
        
        # Handle remote packages
        path = config.get("path", "")
        ref = config.get("ref", {})
        ref_type = ref.get("type", "branch")
        ref_value = ref.get("value", "main")
        
        cache_key = self.get_cache_key(repo, path, ref_type, ref_value)
        cache_path = self.get_cache_path(cache_key)
        
        # Clone if needed
        if not cache_path.exists():
            commit = self.sparse_checkout_package(repo_url, ref_type, ref_value, path, cache_path)
            if not commit:
                return False
        
        self.discovered[name] = self._prepare_remote_package(
            name, config, cache_key, cache_path
        )
        return True
    
    def _run_install_sequence(self, install_order):
        """
        Run the common install sequence: install packages, save lockfile, create symlinks, generate env.
        
        Returns:
            int: Number of successfully installed packages
        """
        self.packages_dir.mkdir(parents=True, exist_ok=True)
        
        lockfile_data = {"packages": {}, "installation_order": install_order}
        success_count = 0
        
        for name in install_order:
            pkg_info = self.discovered.get(name)
            if not pkg_info:
                print("  ✗ Package info not found: {}".format(name))
                continue
            
            result = self.install_package(name, pkg_info)
            if result:
                lockfile_data["packages"][name] = result
                success_count += 1
        
        if success_count > 0:
            print("💾 Saving lockfile...")
            self.save_lockfile(lockfile_data)
            
            print("🔗 Creating dependency symlinks...")
            self.create_dependency_symlinks()
            
            print("📝 Generating environment file...")
            self.generate_env_file()
        
        return success_count
    
    def load_lockfile(self):
        """Load and parse lockfile"""
        if not self.lockfile.exists():
            return None
        
        try:
            return self._load_json_file(self.lockfile, "lockfile")
        except Exception:
            return None
    
    def save_lockfile(self, lockfile_data):
        """Save lockfile with proper formatting"""
        with open(self.lockfile, 'w') as f:
            json.dump(lockfile_data, f, indent=4)
    
    def verify_package_integrity(self, name, expected_info):
        """
        Verify that an installed package matches expected state.
        
        Args:
            name: Package name
            expected_info: Expected package info from lockfile
        
        Returns:
            tuple: (is_valid, error_message)
        """
        pkg_path = self.packages_dir / name
        
        # Check if package exists
        if not pkg_path.exists():
            return False, "Package not found"
        
        # For local packages, verify symlink and path
        if expected_info.get("type") == "local":
            if not pkg_path.is_symlink():
                return False, "Expected symlink but found regular directory"
            
            expected_path = Path(expected_info.get("path"))
            actual_target = pkg_path.resolve()
            
            if actual_target != expected_path:
                return False, "Symlink points to {} instead of {}".format(actual_target, expected_path)
            
            return True, None
        
        # For remote packages, verify commit SHA if available
        git_dir = pkg_path / ".git"
        if git_dir.exists():
            # This package has its own git repo (shouldn't happen with our install method)
            return True, "Warning: Package has .git directory (unexpected)"
        
        # For copied packages, we can't verify commit without git metadata
        # Just verify it exists
        return True, None
    
    def install_from_lockfile(self, resolve_deps=True):
        """Install packages using lockfile for reproducible builds."""
        print("🔒 Installing from lockfile (reproducible build)...")
        
        lockfile_data = self.load_lockfile()
        if not lockfile_data:
            print("  ✗ Lockfile not found or invalid, performing fresh install")
            return self.install_fresh(resolve_deps)
        
        packages = lockfile_data.get("packages", {})
        install_order = lockfile_data.get("installation_order", [])
        
        if not packages:
            print("  ✗ No packages in lockfile")
            return 1
        
        print("   Found {} locked packages".format(len(packages)))
        
        # Recreate discovered packages from lockfile
        for name in install_order:
            pkg_info = packages.get(name)
            if not pkg_info:
                continue
            
            # Handle local packages
            if pkg_info.get("type") == "local":
                local_path = Path(pkg_info.get("path"))
                config = {"repo": pkg_info.get("repo"), "path": ""}
                self.discovered[name] = self._prepare_local_package(name, local_path, config)
                continue
            
            # Handle remote packages - extract locked commit
            ref = pkg_info.get("ref", {})
            commit = ref.get("value") if ref.get("type") == "commit" else pkg_info.get("commit")
            
            if not commit or commit == "unknown":
                print("  ⚠️  No commit SHA for {}, skipping".format(name))
                continue
            
            # Build config with locked commit
            config = {
                "repo": pkg_info.get("repo"),
                "path": pkg_info.get("path", ""),
                "ref": {"type": "commit", "value": commit}
            }
            if "original_ref" in pkg_info:
                config["original_ref"] = pkg_info["original_ref"]
            
            # Fetch if needed
            repo_url = self.normalize_repo_url(config["repo"])
            cache_key = self.get_cache_key(config["repo"], config["path"], "commit", commit)
            cache_path = self.get_cache_path(cache_key)
            
            if not cache_path.exists():
                print("📦 Fetching locked version of {}@{}...".format(name, commit[:8]))
                self.sparse_checkout_package(repo_url, "commit", commit, config["path"], cache_path)
            else:
                print("  ✓ Using cached {}@{}".format(name, commit[:8]))
            
            self.discovered[name] = self._prepare_remote_package(name, config, cache_key, cache_path)
        
        # Run common install sequence
        success_count = self._run_install_sequence(install_order)
        
        print("✅ Installed {} package(s) from lockfile".format(success_count))
        return 0
    
    def install_fresh(self, resolve_deps=True):
        """Perform fresh install, discovering dependencies and creating new lockfile."""
        print("📋 Loading configuration...")
        
        # Load and merge packages
        manifest_packages = self.load_manifest()
        if not manifest_packages:
            print("Error: No packages defined in manifest")
            return 1
        
        local_packages = self.load_local_overrides()
        root_packages = {**manifest_packages, **local_packages}
        
        print("   Loaded {} package(s) ({} from manifest, {} local overrides)".format(
            len(root_packages), len(manifest_packages), len(local_packages)
        ))
        
        if resolve_deps:
            # Full dependency resolution
            print("🔍 Discovering dependencies...")
            self.discover_dependencies(root_packages, local_overrides=local_packages)
            print("   Found {} total packages".format(len(self.discovered)))
            
            print("📦 Planning installation order...")
            install_order = self.topological_sort()
            print("   Order: {}".format(" -> ".join(install_order)))
            print("📥 Installing {} package(s)...".format(len(install_order)))
        else:
            # Flat install
            print("📥 Installing {} package(s)...".format(len(root_packages)))
            install_order = list(root_packages.keys())
            
            # Prepare packages for installation
            for name, config in root_packages.items():
                self._setup_package_for_install(name, config)
        
        # Run common install sequence
        success_count = self._run_install_sequence(install_order)
        
        print("✅ Installation complete! ({}/{} packages)".format(success_count, len(install_order)))
        return 0
    
    def update_gitignore(self):
        """Add git-pm entries to .gitignore if they don't exist"""
        gitignore_path = self.project_root / ".gitignore"
        
        # Entries that should be in .gitignore
        required_entries = [
            ".git-packages/",
            ".git-pm.env",
            "git-pm.local",
            "git-pm.lock"
        ]
        
        # Read existing .gitignore
        existing_lines = []
        if gitignore_path.exists():
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                existing_lines = [line.rstrip() for line in f.readlines()]
        
        # Check which entries are missing
        missing_entries = []
        for entry in required_entries:
            # Check if entry exists (exact match or with trailing slash variants)
            entry_variants = [entry, entry.rstrip('/')]
            if not any(line.rstrip('/') in entry_variants for line in existing_lines):
                missing_entries.append(entry)
        
        # Add missing entries
        if missing_entries:
            print("📝 Updating .gitignore...")
            
            # Create .gitignore if it doesn't exist
            if not gitignore_path.exists():
                print("  ✓ Created .gitignore")
            
            with open(gitignore_path, 'a', encoding='utf-8') as f:
                # Add newline if file doesn't end with one
                if existing_lines and existing_lines[-1]:
                    f.write('\n')
                
                # Add missing entries
                for entry in missing_entries:
                    f.write(entry + '\n')
                    print("  ✓ Added: {}".format(entry))
        else:
            # Check if .gitignore exists
            if gitignore_path.exists():
                print("✓ .gitignore up to date")
    
    def cmd_install(self, resolve_deps=True, manage_gitignore=True, force_fresh=False):
        """
        Install all packages.
        
        Args:
            resolve_deps: Whether to resolve dependencies
            manage_gitignore: Whether to update .gitignore
            force_fresh: Force fresh install, ignore lockfile
        """
        print("🚀 git-pm install{}".format(" (dependency resolution)" if resolve_deps else " (flat)"))
        
        if not self.check_git():
            return 1
        
        # Manage .gitignore entries (unless disabled)
        if manage_gitignore:
            self.update_gitignore()
        
        # Check if lockfile exists and should be used
        if not force_fresh and self.lockfile.exists():
            print("📋 Lockfile found, using for reproducible build")
            print("   (Use --force-fresh to ignore lockfile)")
            return self.install_from_lockfile(resolve_deps)
        else:
            if force_fresh:
                print("📋 Forcing fresh install (ignoring lockfile)")
            return self.install_fresh(resolve_deps)
    
    def generate_env_file(self):
        """Generate .git-pm.env file with package locations"""
        env_file = self.project_root / ".git-pm.env"
        
        # Absolute path to .git-packages
        packages_abs = self.packages_dir.resolve()
        
        with open(env_file, 'w') as f:
            f.write("# git-pm environment configuration\n")
            f.write("# Generated by git-pm - do not edit manually\n\n")
            f.write("# Usage:\n")
            f.write("#   Shell scripts:    source .git-pm.env\n")
            f.write("#   Terraform:        Use symlinks in .git-packages/*/git-packages/\n")
            f.write("#   Python/Node:      Load and parse this file\n")
            f.write("#   Makefiles:        include .git-pm.env\n\n")
            
            # Main packages directory
            f.write("# Root packages directory (absolute path)\n")
            f.write("export GIT_PM_PACKAGES_DIR=\"{}\"\n".format(packages_abs))
            f.write("export GIT_PM_PROJECT_ROOT=\"{}\"\n\n".format(self.project_root.resolve()))
            
            # Relative path from any package to packages dir
            f.write("# Relative path from package to packages directory\n")
            f.write("# Use in Terraform: source = \"${{GIT_PM_REL_PACKAGES_DIR}}/packageA\"\n")
            f.write("export GIT_PM_REL_PACKAGES_DIR=\"../\"\n\n")
            
            # Individual package paths (absolute)
            f.write("# Individual package paths (absolute)\n")
            for name in sorted(self.discovered.keys()):
                pkg_path = packages_abs / name
                if pkg_path.exists():
                    # Convert package name to valid env var name (replace - and / with _)
                    env_name = "GIT_PM_PACKAGE_{}".format(
                        name.upper().replace('-', '_').replace('/', '_').replace('.', '_')
                    )
                    f.write("export {}=\"{}\"\n".format(env_name, pkg_path))
            
            # Add helper for Terraform variable file generation
            f.write("\n# Generate Terraform variable file with package paths\n")
            f.write("# Usage: source .git-pm.env && git-pm-generate-tfvars > packages.auto.tfvars\n")
            f.write("git-pm-generate-tfvars() {\n")
            f.write("  echo '# Auto-generated package paths'\n")
            f.write("  echo 'git_pm_packages_dir = \"{}\"'\n".format(packages_abs))
            for name in sorted(self.discovered.keys()):
                pkg_path = packages_abs / name
                if pkg_path.exists():
                    var_name = name.replace('-', '_').replace('/', '_')
                    f.write("  echo '{}_path = \"{}\"'\n".format(var_name, pkg_path))
            f.write("}\n")
        
        print("  ✓ Created .git-pm.env")
    
    def check_symlink_support(self):
        """Check if symlinks are supported on this system"""
        if sys.platform != 'win32':
            return True  # Unix systems always support symlinks
        
        # Windows: Test symlink creation
        test_dir = self.project_root / ".git-pm-symlink-test"
        test_link = self.project_root / ".git-pm-symlink-test-link"
        
        try:
            test_dir.mkdir(exist_ok=True)
            test_link.symlink_to(test_dir, target_is_directory=True)
            test_link.unlink()
            test_dir.rmdir()
            return True
        except OSError as e:
            if test_link.exists():
                test_link.unlink()
            if test_dir.exists():
                test_dir.rmdir()
            
            # Check for specific Windows error
            if "WinError 1314" in str(e):
                return "privilege"  # Need admin or Developer Mode
            return False
    
    def create_dependency_symlinks(self):
        """Create .git-packages symlinks inside packages for their dependencies"""
        # Check symlink support
        symlink_support = self.check_symlink_support()
        
        if symlink_support == "privilege":
            print("  ⚠️  Windows: Symlinks require Administrator privileges or Developer Mode")
            print("     To enable Developer Mode:")
            print("     Settings → Update & Security → For developers → Developer Mode")
            print("     ")
            print("     Falling back to junction points (Windows alternative)...")
            use_junctions = True
        elif not symlink_support:
            print("  ⚠️  Symlinks not supported on this system")
            print("     Dependencies will use absolute paths in .git-pm.env instead")
            return
        else:
            use_junctions = False
        
        for name, pkg_info in self.discovered.items():
            dependencies = pkg_info.get("dependencies", {})
            if not dependencies:
                continue
            
            pkg_dir = self.packages_dir / name
            if not pkg_dir.exists():
                continue
            
            # Create .git-packages directory inside the package
            pkg_deps_dir = pkg_dir / ".git-packages"
            pkg_deps_dir.mkdir(exist_ok=True)
            
            # Create symlinks to sibling packages
            for dep_name in dependencies.keys():
                dep_link = pkg_deps_dir / dep_name
                dep_target = Path("..") / ".." / dep_name  # ../../dep_name
                dep_target_abs = (pkg_deps_dir / dep_target).resolve()
                
                # Remove existing link/directory
                if dep_link.is_symlink() or (sys.platform == 'win32' and dep_link.exists() and dep_link.is_dir()):
                    try:
                        dep_link.unlink()
                    except:
                        pass
                elif dep_link.exists():
                    continue  # Don't overwrite real directories
                
                # Create symlink or junction
                try:
                    if sys.platform == 'win32' and use_junctions:
                        # Use junction point on Windows (doesn't require privileges)
                        import subprocess
                        result = subprocess.run(
                            ['cmd', '/c', 'mklink', '/J', str(dep_link), str(dep_target_abs)],
                            capture_output=True,
                            text=True
                        )
                        if result.returncode == 0:
                            print("  ✓ {}/{} -> {} (junction)".format(name, dep_name, dep_name))
                        else:
                            print("  ⚠ Failed to create junction for {}/{}: {}".format(name, dep_name, result.stderr.strip()))
                    else:
                        # Use symlink on Unix or Windows with Developer Mode
                        dep_link.symlink_to(dep_target, target_is_directory=True)
                        print("  ✓ {}/{} -> {}".format(name, dep_name, dep_name))
                except OSError as e:
                    if "WinError 1314" in str(e):
                        print("  ⚠ {}/{}: Requires Administrator or Developer Mode".format(name, dep_name))
                        print("     See: https://docs.microsoft.com/en-us/windows/apps/get-started/enable-your-device-for-development")
                    else:
                        print("  ⚠ Failed to create symlink for {}/{}: {}".format(name, dep_name, e))
                except Exception as e:
                    print("  ⚠ Failed to create symlink for {}/{}: {}".format(name, dep_name, e))
    
    def cmd_update(self):
        """Update packages (branches only)"""
        print("🔄 git-pm update")
        
        if not self.check_git():
            return 1
        
        print("📋 Loading configuration...")
        
        # Load manifest and local packages
        manifest_packages = self.load_manifest()
        if not manifest_packages:
            print("Error: No packages in manifest")
            return 1
        
        local_packages = self.load_local_overrides()
        
        # Merge packages
        all_packages = {**manifest_packages, **local_packages}
        
        print("🔄 Updating packages...")
        
        updated = 0
        skipped = 0
        
        for name, config in all_packages.items():
            repo = config.get("repo")
            repo_url = self.normalize_repo_url(repo)
            
            # Skip local packages - can't update local files
            if self.is_local_package(repo_url):
                print("📦 Skipping {} (local package)".format(name))
                skipped += 1
                continue
            
            ref = config.get("ref", {})
            ref_type = ref.get("type", "branch")
            
            # Only update branch references
            if ref_type == "branch":
                print("📦 Updating {}...".format(name))
                
                path = config.get("path", "")
                ref_value = ref.get("value", "main")
                
                # Resolve branch to latest commit
                commit_sha = self.resolve_branch_to_commit(repo_url, ref_value)
                if not commit_sha:
                    continue
                
                # Update config with new commit
                config["ref"] = {"type": "commit", "value": commit_sha}
                config["original_ref"] = {"type": "branch", "value": ref_value}
                
                # Force re-clone
                cache_key = self.get_cache_key(repo, path, "commit", commit_sha)
                cache_path = self.get_cache_path(cache_key)
                
                if cache_path.exists():
                    shutil.rmtree(cache_path)
                
                self.sparse_checkout_package(repo_url, "commit", commit_sha, path, cache_path)
                
                # Prepare and install
                self.discovered[name] = self._prepare_remote_package(name, config, cache_key, cache_path)
                
                if self.install_package(name, self.discovered[name]):
                    updated += 1
            else:
                print("📦 Skipping {} (not a branch reference)".format(name))
                skipped += 1
        
        print("✅ Updated {} package(s), skipped {}".format(updated, skipped))
        return 0
    
    def _rmtree_windows_safe(self, path):
        """Remove directory tree, handling Windows read-only files"""
        def handle_remove_readonly(func, path, exc):
            """Error handler for Windows read-only files"""
            import stat
            if not os.access(path, os.W_OK):
                # File is read-only, try to make it writable
                os.chmod(path, stat.S_IWUSR | stat.S_IRUSR)
                func(path)
            else:
                raise
        
        if sys.platform == 'win32':
            # On Windows, use error handler for read-only files
            shutil.rmtree(path, onerror=handle_remove_readonly)
        else:
            # On Unix, standard rmtree works fine
            shutil.rmtree(path)
    
    def cmd_clean(self):
        """Remove all installed packages"""
        print("🧹 git-pm clean")
        
        if self.packages_dir.exists():
            self._rmtree_windows_safe(self.packages_dir)
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
        
        lockfile = self._load_json_file(self.lockfile, "lockfile")
        
        packages = lockfile.get("packages", {})
        if not packages:
            print("No packages in lockfile")
            return 0
        
        print("\nInstalled packages:")
        for name, info in packages.items():
            if info.get("type") == "local":
                symlink_info = " (symlinked)" if info.get("symlinked") else ""
                print("  {} - local: {}{}".format(name, info.get("path"), symlink_info))
            else:
                ref_str = "{}:{}".format(
                    info.get("ref", {}).get("type"),
                    info.get("ref", {}).get("value", "")[:8]
                )
                deps = info.get("dependencies", [])
                deps_str = " [deps: {}]".format(", ".join(deps)) if deps else ""
                print("  {} - {}@{} [{}]{}".format(
                    name,
                    info.get("repo"),
                    ref_str,
                    info.get("commit", "")[:8],
                    deps_str
                ))
        
        # Show installation order if available
        order = lockfile.get("installation_order", [])
        if order:
            print("\nInstallation order: {}".format(" -> ".join(order)))
        
        return 0
    
    def cmd_verify(self):
        """Verify integrity of installed packages against lockfile"""
        print("🔍 git-pm verify")
        
        # Check if lockfile exists
        if not self.lockfile.exists():
            print("✗ No lockfile found")
            print("  Run 'git-pm install' to create a lockfile")
            return 1
        
        # Check if packages directory exists
        if not self.packages_dir.exists():
            print("✗ No packages installed (.git-packages directory not found)")
            return 1
        
        # Load lockfile
        lockfile_data = self.load_lockfile()
        if not lockfile_data:
            print("✗ Failed to load lockfile")
            return 1
        
        packages = lockfile_data.get("packages", {})
        if not packages:
            print("✗ No packages in lockfile")
            return 1
        
        print("Verifying {} package(s)...\n".format(len(packages)))
        
        valid_count = 0
        invalid_count = 0
        warnings = []
        errors = []
        
        for name, expected_info in packages.items():
            is_valid, error_msg = self.verify_package_integrity(name, expected_info)
            
            if is_valid:
                if error_msg and error_msg.startswith("Warning"):
                    print("  ⚠️  {} - {}".format(name, error_msg))
                    warnings.append((name, error_msg))
                    valid_count += 1
                else:
                    print("  ✓ {}".format(name))
                    valid_count += 1
            else:
                print("  ✗ {} - {}".format(name, error_msg))
                errors.append((name, error_msg))
                invalid_count += 1
        
        print("\n" + "=" * 60)
        print("Verification Summary:")
        print("  ✓ Valid: {}".format(valid_count))
        
        if warnings:
            print("  ⚠️  Warnings: {}".format(len(warnings)))
        
        if invalid_count > 0:
            print("  ✗ Invalid: {}".format(invalid_count))
            print("\nErrors found:")
            for name, error_msg in errors:
                print("  • {}: {}".format(name, error_msg))
            print("\nRun 'git-pm install --force-fresh' to fix integrity issues")
            return 1
        else:
            print("\n✅ All packages verified successfully!")
            if warnings:
                print("   (with {} warning(s))".format(len(warnings)))
            return 0
    
    def cmd_add(self, name, repo, path, ref_type, ref_value):
        """Add a package to manifest"""
        print("📦 git-pm add")
        
        # Determine where to create the manifest
        cwd = Path.cwd()
        
        if cwd == self.project_root or self.manifest_file.exists():
            manifest_dir = self.project_root
        else:
            manifest_dir = cwd
        
        manifest_file = manifest_dir / "git-pm.json"
        
        if manifest_file.exists():
            manifest = self._load_json_file(manifest_file, "manifest")
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
            json.dump(manifest, f, indent=4)
        
        print("✓ Package '{}' added to manifest".format(name))
        print("\nPackage configuration:")
        print("  Name: {}".format(name))
        print("  Repo: {}".format(repo))
        print("  Path: {}".format(path))
        print("  Ref:  {}:{}".format(ref_type, ref_value))
        print("\nRun 'git-pm install' to install the package")
        
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="git-pm: Git Package Manager with dependency resolution",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--version", action="version", version="git-pm {}".format(__version__))
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Install command
    install_parser = subparsers.add_parser("install", help="Install packages from manifest")
    install_parser.add_argument(
        "--no-resolve-deps",
        action="store_true",
        help="Disable dependency resolution (flat install)"
    )
    install_parser.add_argument(
        "--no-gitignore",
        action="store_true",
        help="Skip automatic .gitignore management"
    )
    install_parser.add_argument(
        "--force-fresh",
        action="store_true",
        help="Force fresh install, ignore lockfile"
    )
    
    subparsers.add_parser("update", help="Update packages to latest versions (branches only)")
    subparsers.add_parser("clean", help="Remove all installed packages")
    subparsers.add_parser("list", help="List installed packages")
    subparsers.add_parser("verify", help="Verify integrity of installed packages against lockfile")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add a package to the manifest")
    add_parser.add_argument("name", help="Package name")
    add_parser.add_argument("repo", help="Repository identifier")
    add_parser.add_argument("--path", default="", help="Path within repository")
    add_parser.add_argument(
        "--ref-type",
        choices=["tag", "branch", "commit"],
        default="branch",
        help="Reference type"
    )
    add_parser.add_argument("--ref-value", default="main", help="Reference value")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    gpm = GitPM()
    
    if args.command == "install":
        return gpm.cmd_install(
            resolve_deps=not args.no_resolve_deps,
            manage_gitignore=not args.no_gitignore,
            force_fresh=args.force_fresh
        )
    elif args.command == "update":
        return gpm.cmd_update()
    elif args.command == "clean":
        return gpm.cmd_clean()
    elif args.command == "list":
        return gpm.cmd_list()
    elif args.command == "verify":
        return gpm.cmd_verify()
    elif args.command == "add":
        return gpm.cmd_add(args.name, args.repo, args.path, args.ref_type, args.ref_value)
    
    return 1


if __name__ == "__main__":
    sys.exit(main())