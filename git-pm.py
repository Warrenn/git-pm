#!/usr/bin/env python3
"""
git-pm: Git Package Manager
A package manager that uses git sparse-checkout to manage dependencies with full dependency resolution.

Version 0.2.0 - Full dependency resolution with explicit versions
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

__version__ = "0.2.0"


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
        # Find project root by looking for git-pm.yaml
        self.project_root = self._find_project_root()
        
        self.config = self.load_config()
        self.manifest_file = self.project_root / "git-pm.yaml"
        self.local_override_file = self.project_root / "git-pm.local.yaml"
        self.lockfile = self.project_root / "git-pm.lock"
        self.packages_dir = self.project_root / self.config["packages_dir"]
        
        # Dependency resolution state
        self.discovered = {}  # All discovered packages
        self.branch_commits = {}  # Resolved branch -> commit mappings
    
    def _find_project_root(self):
        """Find project root by looking for git-pm.yaml"""
        current = Path.cwd()
        
        # Check current directory first
        if (current / "git-pm.yaml").exists():
            return current
        
        # Check parent directories
        for parent in current.parents:
            if (parent / "git-pm.yaml").exists():
                return parent
        
        # No manifest found, use current directory
        return current
    
    def load_config(self):
        """Load configuration with defaults"""
        config = {
            "packages_dir": ".git-packages",
            "cache_dir": str(Path.home() / ".cache" / "git-pm"),
            "git_protocol": {},
            "url_patterns": {},
            "azure_devops_pat": os.getenv("AZURE_DEVOPS_PAT", "")
        }
        
        # Load user config
        config_file = self.project_root / "git-pm.config.yaml" if hasattr(self, 'project_root') else Path.cwd() / "git-pm.config.yaml"
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
            print("Error: git-pm.yaml not found in {}".format(self.project_root))
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
    
    def discover_dependencies(self, packages, depth=0, parent_chain=None):
        """Recursively discover all dependencies"""
        if parent_chain is None:
            parent_chain = []
        
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
            
            # Resolve branch to commit if needed
            ref = config.get("ref", {})
            ref_type = ref.get("type", "branch")
            ref_value = ref.get("value", "main")
            
            if ref_type == "branch":
                repo_url = self.normalize_repo_url(config["repo"])
                commit_sha = self.resolve_branch_to_commit(repo_url, ref_value)
                if commit_sha:
                    # Update config to use resolved commit
                    config = dict(config)
                    config["ref"] = {"type": "commit", "value": commit_sha}
                    config["original_ref"] = {"type": "branch", "value": ref_value}
            
            # Install to temp location to discover dependencies
            repo = config.get("repo")
            path = config.get("path", "")
            ref = config.get("ref", {})
            ref_type = ref.get("type", "commit")
            ref_value = ref.get("value", "main")
            
            repo_url = self.normalize_repo_url(repo)
            cache_key = self.get_cache_key(repo, path, ref_type, ref_value)
            cache_path = self.get_cache_path(cache_key)
            
            # Clone if not cached (for explicit refs) or always for branches
            needs_clone = not cache_path.exists()
            if config.get("original_ref", {}).get("type") == "branch":
                needs_clone = True  # Always pull latest for branches
            
            if needs_clone:
                commit_sha = self.sparse_checkout_package(repo_url, ref_type, ref_value, path, cache_path)
                if not commit_sha:
                    continue
            else:
                print("  Found in cache: {}".format(cache_key))
            
            # Look for git-pm.yaml in the package
            pkg_manifest_path = cache_path / path / "git-pm.yaml" if path else cache_path / "git-pm.yaml"
            
            nested_deps = {}
            if pkg_manifest_path.exists():
                with open(pkg_manifest_path, 'r') as f:
                    pkg_data = SimpleYAML.load(f)
                    nested_deps = pkg_data.get("packages", {})
                
                if nested_deps:
                    print("{}  Found {} dependencies".format("  " * depth, len(nested_deps)))
                    # Recursively discover
                    discovered_nested = self.discover_dependencies(
                        nested_deps,
                        depth + 1,
                        parent_chain + [name]
                    )
                    all_discovered.update(discovered_nested)
            
            # Store discovered package
            self.discovered[name] = {
                "config": config,
                "dependencies": nested_deps,
                "depth": depth,
                "cache_key": cache_key,
                "cache_path": cache_path
            }
            all_discovered[name] = self.discovered[name]
        
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
    
    def install_package(self, name, pkg_info, overrides):
        """Install a single package"""
        print("📦 Installing {}...".format(name))
        
        config = pkg_info["config"]
        cache_path = pkg_info["cache_path"]
        path = config.get("path", "")
        
        # Check for local override
        if name in overrides:
            override = overrides[name]
            if override.get("type") == "local":
                local_path = Path(override["path"])
                if not local_path.is_absolute():
                    local_path = (self.project_root / local_path).resolve()
                
                if not local_path.exists():
                    print("  ✗ Local path does not exist: {}".format(local_path))
                    return None
                
                dest_path = self.packages_dir / name
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Use symlink for local overrides
                if self.copy_or_link_package(local_path.parent, local_path.name, dest_path, use_symlink=True):
                    print("  Override: {} -> local (symlinked)".format(name))
                    return {
                        "type": "local",
                        "path": str(local_path),
                        "symlinked": True,
                        "installed_at": datetime.now().isoformat()
                    }
                return None
        
        # Install from cache
        dest_path = self.packages_dir / name
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
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
    
    def cmd_install(self, resolve_deps=True):
        """Install all packages"""
        print("🚀 git-pm install{}".format(" (dependency resolution)" if resolve_deps else " (flat)"))
        
        if not self.check_git():
            return 1
        
        print("📋 Loading configuration...")
        
        root_packages = self.load_manifest()
        if not root_packages:
            print("Error: No packages defined in manifest")
            return 1
        
        overrides = self.load_local_overrides()
        
        if resolve_deps:
            # Full dependency resolution
            print("🔍 Discovering dependencies...")
            self.discover_dependencies(root_packages)
            print("   Found {} total packages".format(len(self.discovered)))
            
            print("📦 Planning installation order...")
            install_order = self.topological_sort()
            print("   Order: {}".format(" -> ".join(install_order)))
            
            print("📥 Installing {} package(s)...".format(len(install_order)))
        else:
            # Flat install (no dependency resolution)
            print("📥 Installing {} package(s)...".format(len(root_packages)))
            install_order = list(root_packages.keys())
            
            # Prepare discovered info for flat install
            for name, config in root_packages.items():
                repo = config.get("repo")
                path = config.get("path", "")
                ref = config.get("ref", {})
                ref_type = ref.get("type", "branch")
                ref_value = ref.get("value", "main")
                
                repo_url = self.normalize_repo_url(repo)
                cache_key = self.get_cache_key(repo, path, ref_type, ref_value)
                cache_path = self.get_cache_path(cache_key)
                
                # Clone if needed
                if not cache_path.exists():
                    self.sparse_checkout_package(repo_url, ref_type, ref_value, path, cache_path)
                
                self.discovered[name] = {
                    "config": config,
                    "dependencies": {},
                    "depth": 0,
                    "cache_key": cache_key,
                    "cache_path": cache_path
                }
        
        self.packages_dir.mkdir(parents=True, exist_ok=True)
        
        lockfile_data = {"packages": {}, "installation_order": install_order}
        success_count = 0
        
        for name in install_order:
            pkg_info = self.discovered.get(name)
            if not pkg_info:
                print("  ✗ Package info not found: {}".format(name))
                continue
            
            result = self.install_package(name, pkg_info, overrides)
            if result:
                lockfile_data["packages"][name] = result
                success_count += 1
        
        if success_count > 0:
            print("💾 Saving lockfile...")
            with open(self.lockfile, 'w') as f:
                json.dump(lockfile_data, f, indent=2)
        
        print("✅ Installation complete! ({}/{} packages)".format(success_count, len(install_order)))
        return 0
    
    def cmd_update(self):
        """Update packages (branches only)"""
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
                
                # Reinstall
                self.discovered[name] = {
                    "config": config,
                    "dependencies": {},
                    "depth": 0,
                    "cache_key": cache_key,
                    "cache_path": cache_path
                }
                
                overrides = self.load_local_overrides()
                result = self.install_package(name, self.discovered[name], overrides)
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
            lockfile = json.load(f)
        
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
    
    def cmd_add(self, name, repo, path, ref_type, ref_value):
        """Add a package to manifest"""
        print("📦 git-pm add")
        
        # Determine where to create the manifest
        cwd = Path.cwd()
        
        if cwd == self.project_root or self.manifest_file.exists():
            manifest_dir = self.project_root
        else:
            manifest_dir = cwd
        
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
    
    subparsers.add_parser("update", help="Update packages to latest versions (branches only)")
    subparsers.add_parser("clean", help="Remove all installed packages")
    subparsers.add_parser("list", help="List installed packages")
    
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
        return gpm.cmd_install(resolve_deps=not args.no_resolve_deps)
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
