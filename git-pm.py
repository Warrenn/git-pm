#!/usr/bin/env python3
"""
git-pm: Git Package Manager
A package manager that uses git sparse-checkout to manage dependencies with full dependency resolution.

Version 0.4.6 - Full dependency resolution with explicit versions
Requires Python 3.8+ (3.7 may work but is not tested)
"""

import argparse
import hashlib
import json
import os
import re
import urllib.parse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

if sys.platform == 'win32':
    # Set UTF-8 encoding for stdout and stderr
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

__version__ = "0.4.6"


class GitPM:
    def __init__(self):
        # Find project root by looking for git-pm.json
        self.project_root = self._find_project_root()
        
        self.config = self.load_config()
        self.manifest_file = self.project_root / "git-pm.json"
        self.local_override_file = self.project_root / "git-pm.local"
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
    
    def _parse_azure_devops_url(self, repo):
        """
        Parse any Azure DevOps URL format and extract org, project, repo.
        
        Supported formats:
        - https://[user@]dev.azure.com/{org}/{project}/_git/{repo}
        - git@ssh.dev.azure.com:v3/{org}/{project}/{repo}
        - dev.azure.com/{org}/{project}/_git/{repo}
        - dev.azure.com/{org}/{project}/{repo}
        - dev.azure.com:v3/{org}/{project}/{repo}  (malformed but common)
        
        Returns: (org, project, repo) tuple or None if not an Azure DevOps URL
        """
        # Normalize: remove .git suffix if present
        repo = repo.rstrip('/')
        if repo.endswith('.git'):
            repo = repo[:-4]
        
        # Pattern 1: SSH format - git@ssh.dev.azure.com:v3/{org}/{project}/{repo}
        ssh_match = re.match(r'^git@ssh\.dev\.azure\.com:v3/([^/]+)/([^/]+)/(.+)$', repo)
        if ssh_match:
            org, project, repo_name = ssh_match.groups()
            # SSH URLs may have URL-encoded project names, decode them for consistency
            return (urllib.parse.unquote(org), urllib.parse.unquote(project), urllib.parse.unquote(repo_name))
        
        # Pattern 2: Malformed hybrid - dev.azure.com:v3/{org}/{project}/{repo}
        # This is a common mistake mixing HTTPS domain with SSH path style
        hybrid_match = re.match(r'^dev\.azure\.com:v3/([^/]+)/([^/]+)/(.+)$', repo)
        if hybrid_match:
            org, project, repo_name = hybrid_match.groups()
            return (urllib.parse.unquote(org), urllib.parse.unquote(project), urllib.parse.unquote(repo_name))
        
        # Pattern 3: HTTPS format - https://[user@]dev.azure.com/{org}/{project}/_git/{repo}
        https_match = re.match(r'^https://(?:[^@]+@)?dev\.azure\.com/([^/]+)/([^/]+)/_git/(.+)$', repo)
        if https_match:
            org, project, repo_name = https_match.groups()
            return (urllib.parse.unquote(org), urllib.parse.unquote(project), urllib.parse.unquote(repo_name))
        
        # Pattern 4: Shorthand with /_git/ - dev.azure.com/{org}/{project}/_git/{repo}
        shorthand_git_match = re.match(r'^dev\.azure\.com/([^/]+)/([^/]+)/_git/(.+)$', repo)
        if shorthand_git_match:
            org, project, repo_name = shorthand_git_match.groups()
            return (urllib.parse.unquote(org), urllib.parse.unquote(project), urllib.parse.unquote(repo_name))
        
        # Pattern 5: Shorthand without /_git/ - dev.azure.com/{org}/{project}/{repo}
        shorthand_match = re.match(r'^dev\.azure\.com/([^/]+)/([^/]+)/([^/]+)$', repo)
        if shorthand_match:
            org, project, repo_name = shorthand_match.groups()
            return (urllib.parse.unquote(org), urllib.parse.unquote(project), urllib.parse.unquote(repo_name))
        
        return None


    # ============================================================================
    # NEW METHOD: Add this to the GitPM class (after _parse_azure_devops_url)
    # ============================================================================

    def _build_azure_devops_url(self, org, project, repo, protocol='https', token=None):
        """
        Build Azure DevOps URL in the specified protocol.
        
        Args:
            org: Organization name
            project: Project name  
            repo: Repository name
            protocol: 'https' or 'ssh'
            token: Optional PAT for HTTPS authentication (embedded in URL)
                If None and SYSTEM_ACCESSTOKEN is set, URL is built without token
                (authentication handled via git http.extraheader)
        
        Returns: Full URL string
        """
        if protocol == 'ssh':
            return "git@ssh.dev.azure.com:v3/{}/{}/{}".format(org, project, repo)
        else:
            # HTTPS format - URL encode project name for spaces
            project_encoded = urllib.parse.quote(project, safe='')
            if token:
                return "https://{}@dev.azure.com/{}/{}/_git/{}".format(token, org, project_encoded, repo)
            return "https://dev.azure.com/{}/{}/_git/{}".format(org, project_encoded, repo)

    def _configure_azure_devops_auth(self):
        """
        Configure git authentication for Azure DevOps using SYSTEM_ACCESSTOKEN.
        
        This sets up git's http.extraheader to use bearer token authentication,
        which is the recommended approach for Azure DevOps pipelines as it:
        - Keeps tokens out of URLs and logs
        - Works with System.AccessToken in Azure Pipelines
        - Supports scoped access tokens
        
        Call this method before any git operations when SYSTEM_ACCESSTOKEN is set.
        
        Returns: True if auth was configured, False otherwise
        """
        system_token = os.getenv("SYSTEM_ACCESSTOKEN")
        
        if not system_token:
            return False
        
        # Configure git to use bearer token for Azure DevOps
        # This applies to all dev.azure.com URLs
        try:
            # Set the authorization header for Azure DevOps
            auth_header = "AUTHORIZATION: bearer {}".format(system_token)
            
            subprocess.run(
                ["git", "config", "--global", "http.https://dev.azure.com/.extraheader", auth_header],
                check=True,
                capture_output=True
            )
            
            print("  ✓ Configured Azure DevOps bearer token authentication")
            return True
            
        except subprocess.CalledProcessError as e:
            print("  ⚠ Failed to configure Azure DevOps authentication: {}".format(e))
            return False


    def _cleanup_azure_devops_auth(self):
        """
        Remove git authentication configuration for Azure DevOps.
        
        Call this after git operations to clean up the global config.
        This is optional but recommended for security in shared environments.
        """
        try:
            subprocess.run(
                ["git", "config", "--global", "--unset", "http.https://dev.azure.com/.extraheader"],
                capture_output=True
            )
        except subprocess.CalledProcessError:
            pass  # Ignore errors (config may not exist)

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
        
        # Check if this is an Azure DevOps URL (any format)
        ado_parts = self._parse_azure_devops_url(repo)
        if ado_parts:
            org, project, repo_name = ado_parts
            
            # Determine protocol preference (default to ssh for backward compatibility)
            protocol = 'ssh'
            if "git_protocol" in self.config and "dev.azure.com" in self.config["git_protocol"]:
                protocol = self.config["git_protocol"]["dev.azure.com"]
            
            # Check for authentication tokens
            # Priority: AZURE_DEVOPS_PAT (embedded in URL) > SYSTEM_ACCESSTOKEN (via http.extraheader)
            pat_token = self.config.get("azure_devops_pat") or os.getenv("GIT_PM_TOKEN_dev_azure_com")
            system_token = os.getenv("SYSTEM_ACCESSTOKEN")
            
            if pat_token:
                # PAT token - embed in URL, force HTTPS
                protocol = 'https'
                return self._build_azure_devops_url(org, project, repo_name, protocol, pat_token)
            elif system_token:
                # System token - use http.extraheader (configured separately), force HTTPS
                # Note: _configure_azure_devops_auth() must be called before git operations
                protocol = 'https'
                return self._build_azure_devops_url(org, project, repo_name, protocol, None)
            
            return self._build_azure_devops_url(org, project, repo_name, protocol, None)
        
        # Already a full URL (http/https/git@) - pass through for non-Azure DevOps
        if repo.startswith(("http://", "https://", "git@")):
            return repo
        
        if "/" not in repo:
            return repo
        
        canonical_repo = repo
        domain = canonical_repo.split("/")[0]
        path = "/".join(canonical_repo.split("/")[1:])
        
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
        
        # Check for generic token in environment
        env_token_key = "GIT_PM_TOKEN_{}".format(domain.replace(".", "_"))
        token = os.getenv(env_token_key)
        
        if token:
            if "github.com" in domain:
                return "https://{}@github.com/{}.git".format(token, path)
            else:
                return "https://oauth2:{}@{}/{}.git".format(token, domain, path)
        
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
        Run the common install sequence: install packages, create symlinks, generate env.
        
        Returns:
            int: Number of successfully installed packages
        """
        self.packages_dir.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        
        for name in install_order:
            pkg_info = self.discovered.get(name)
            if not pkg_info:
                print("  ✗ Package info not found: {}".format(name))
                continue
            
            result = self.install_package(name, pkg_info)
            if result:
                success_count += 1
        
        if success_count > 0:
            
            print("🔗 Creating dependency symlinks...")
            self.create_dependency_symlinks()
            
            print("📝 Generating environment file...")
            self.generate_env_file()
        
        return success_count
    
    def install_fresh(self):
        """Perform fresh install, discovering dependencies."""
        print("📋 Loading configuration...")
        
        # Load and merge packages
        manifest_packages = self.load_manifest()
        if not manifest_packages:
            print("Error: No packages defined in manifest")
            return 1
        
        local_packages = self.load_local_overrides()
        root_packages = {**manifest_packages, **local_packages}
        
        print(f"   Loaded {len(root_packages)} package(s) ({len(manifest_packages)} from manifest, {len(local_packages)} local overrides)")
        
        # Full dependency resolution
        print("🔍 Discovering dependencies...")
        self.discover_dependencies(root_packages, local_overrides=local_packages)
        print(f"   Found {len(self.discovered)} total packages")
        print("📦 Planning installation order...")
        install_order = self.topological_sort()
        print(f"   Order: {' -> '.join(install_order)}")
        print(f"📥 Installing {len(install_order)} package(s)...")
        # Run common install sequence
        success_count = self._run_install_sequence(install_order)
        
        print(f"✅ Installation complete! ({success_count}/{len(install_order)} packages)")
        return 0
    
    def update_gitignore(self):
        """Add git-pm entries to .gitignore if they don't exist"""
        gitignore_path = self.project_root / ".gitignore"
        
        # Entries that should be in .gitignore
        required_entries = [
            ".git-packages/",
            ".git-pm.env",
            "git-pm.local",
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
    
    def cmd_install(self, manage_gitignore=True):
        """
        Install all packages.
        
        Args:
            manage_gitignore: Whether to update .gitignore
        """
        print("🚀 git-pm install")
        
        self._configure_azure_devops_auth()
        
        if not self.check_git():
            return 1
        
        # Manage .gitignore entries (unless disabled)
        if manage_gitignore:
            self.update_gitignore()
        
        return self.install_fresh()
    
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
        
        print("✅ Clean complete!")
        return 0
    
    def cmd_remove(self, package_name, auto_confirm=False):
        """Remove a package from manifests and optionally from disk"""
        print("🗑️  git-pm remove")
        print(f"Package: {package_name}")
        print()
        
        # Load manifests
        manifest_packages = {}
        local_packages = {}
        
        if self.manifest_file.exists():
            manifest = self._load_json_file(self.manifest_file, "manifest")
            manifest_packages = manifest.get("packages", {})
        
        if self.local_override_file.exists():
            local_override = self._load_json_file(self.local_override_file, "local override")
            local_packages = local_override.get("packages", {})
        
        # Check if package exists in either manifest
        in_manifest = package_name in manifest_packages
        in_local = package_name in local_packages
        
        if not in_manifest and not in_local:
            print(f"⚠️  Package '{package_name}' not found in git-pm.json or git-pm.local")
            return 1
        
        print("📋 Analyzing dependencies...")
        
        # Build complete dependency graph of what will remain
        # After removing package_name from manifests
        remaining_in_manifest = {k: v for k, v in manifest_packages.items() if k != package_name}
        remaining_in_local = {k: v for k, v in local_packages.items() if k != package_name}
        
        # Find all packages that will still be needed after removal
        needed_packages = set()
        
        def collect_dependencies(pkg_name, config, visited=None):
            """Recursively collect all dependencies of a package"""
            if visited is None:
                visited = set()
            
            if pkg_name in visited:
                return
            visited.add(pkg_name)
            needed_packages.add(pkg_name)
            
            # Get package location to read its manifest
            pkg_dir = self.packages_dir / pkg_name
            pkg_manifest = pkg_dir / "git-pm.json"
            
            if pkg_manifest.exists():
                pkg_data = self._load_json_file(pkg_manifest, f"{pkg_name} manifest")
                pkg_deps = pkg_data.get("packages", {})
                
                for dep_name in pkg_deps:
                    collect_dependencies(dep_name, pkg_deps[dep_name], visited)
        
        # Collect dependencies for all remaining packages
        for pkg_name, config in remaining_in_manifest.items():
            collect_dependencies(pkg_name, config)
        
        for pkg_name, config in remaining_in_local.items():
            collect_dependencies(pkg_name, config)
        
        # Determine what can be removed from disk
        packages_to_remove_from_disk = []
        
        if self.packages_dir.exists():
            for item in self.packages_dir.iterdir():
                if item.is_dir() and item.name not in needed_packages:
                    packages_to_remove_from_disk.append(item.name)
        
        # Show preview
        print()
        print("📦 Removal plan:")
        print()
        
        if in_manifest:
            print(f"  ✓ Remove from git-pm.json: {package_name}")
        
        if in_local:
            print(f"  ✓ Remove from git-pm.local: {package_name}")
        
        if packages_to_remove_from_disk:
            print()
            print(f"  ✓ Remove from .git-packages/ ({len(packages_to_remove_from_disk)} package(s)):")
            for pkg in sorted(packages_to_remove_from_disk):
                reason = "no longer needed" if pkg != package_name else "explicitly removed"
                print(f"    - {pkg} ({reason})")
        else:
            if package_name not in needed_packages:
                print()
                print(f"  ℹ️  '{package_name}' not in .git-packages/ (already removed or never installed)")
            else:
                print()
                print(f"  ℹ️  '{package_name}' still needed by other packages, keeping in .git-packages/")
        
        # Calculate packages that will remain
        remaining_on_disk = []
        if self.packages_dir.exists():
            for item in self.packages_dir.iterdir():
                if item.is_dir() and item.name not in packages_to_remove_from_disk:
                    remaining_on_disk.append(item.name)
        
        if remaining_on_disk:
            print()
            print(f"  ✓ Keep in .git-packages/ ({len(remaining_on_disk)} package(s)):")
            for pkg in sorted(remaining_on_disk):
                if pkg in needed_packages:
                    print(f"    - {pkg} (still needed)")
        
        # Confirm
        if not auto_confirm:
            print()
            response = input("Proceed with removal? (y/N): ").strip().lower()
            if response != 'y':
                print("Cancelled.")
                return 0
        
        print()
        print("🔧 Removing package...")
        
        # Remove from git-pm.json
        if in_manifest:
            del manifest_packages[package_name]
            manifest["packages"] = manifest_packages
            
            with open(self.manifest_file, 'w') as f:
                json.dump(manifest, f, indent=4)
            
            print(f"  ✓ Removed from {self.manifest_file.name}")
        
        # Remove from git-pm.local
        if in_local:
            del local_packages[package_name]
            local_override["packages"] = local_packages
            
            with open(self.local_override_file, 'w') as f:
                json.dump(local_override, f, indent=4)
            
            print(f"  ✓ Removed from {self.local_override_file.name}")
        
        # Remove from .git-packages/
        if packages_to_remove_from_disk:
            for pkg_name in packages_to_remove_from_disk:
                pkg_dir = self.packages_dir / pkg_name
                if pkg_dir.exists():
                    self._rmtree_windows_safe(pkg_dir)
                    print(f"  ✓ Removed {pkg_name}/ from .git-packages/")
        
        # Update .git-pm.env
        env_file = self.project_root / ".git-pm.env"
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_lines = f.readlines()
            
            # Remove entries for deleted packages
            new_env_lines = []
            for line in env_lines:
                # Keep line if it doesn't reference any removed package
                should_keep = True
                for pkg_name in packages_to_remove_from_disk:
                    # Check for entries like GIT_PM_PACKAGE_pkg_name=...
                    safe_name = pkg_name.replace('-', '_').replace('.', '_')
                    if f"GIT_PM_PACKAGE_{safe_name}=" in line:
                        should_keep = False
                        break
                
                if should_keep:
                    new_env_lines.append(line)
            
            # Write back
            with open(env_file, 'w') as f:
                f.writelines(new_env_lines)
            
            print(f"  ✓ Updated .git-pm.env")
        
        print()
        print(f"✅ Successfully removed '{package_name}'")
        
        if packages_to_remove_from_disk:
            print(f"   Removed {len(packages_to_remove_from_disk)} package(s) from disk")
        
        return 0
    
    def cmd_config(self, key=None, value=None, is_global=False, unset=False, list_all=False):
        """Manage git-pm configuration"""
        
        # Known configuration keys
        KNOWN_KEYS = {
            "packages_dir": "Directory where packages are installed",
            "cache_dir": "Cache directory location",
            "git_protocol": "Git protocol settings (dict)",
            "url_patterns": "URL pattern mappings (dict)",
            "azure_devops_pat": "Azure DevOps Personal Access Token"
        }
        
        # Determine which config file to use
        if is_global:
            config_path = self.get_user_config_path()
            config_type = "user"
        else:
            config_path = self.project_root / 'git-pm.config'
            config_type = "project"
        
        # LIST: Show all configuration
        if list_all:
            print("⚙️  git-pm config")
            print()
            print("Configuration (merged view):")
            print()
            
            # Get defaults
            defaults = {
                "packages_dir": ".git-packages",
                "cache_dir": str(Path.home() / ".cache" / "git-pm"),
                "git_protocol": {},
                "url_patterns": {},
                "azure_devops_pat": os.getenv("AZURE_DEVOPS_PAT", "")
            }
            
            # Get user config
            user_config = self.load_user_config()
            
            # Get project config
            project_config = self.load_project_config()
            
            # Show all keys from defaults
            for config_key in sorted(KNOWN_KEYS.keys()):
                # Determine source
                if config_key in project_config:
                    val = project_config[config_key]
                    source = "project"
                elif config_key in user_config:
                    val = user_config[config_key]
                    source = "user"
                else:
                    val = defaults.get(config_key, "")
                    source = "default"
                
                # Format value for display
                if isinstance(val, dict):
                    val_str = json.dumps(val)
                elif isinstance(val, str) and val == "":
                    val_str = "(empty)"
                else:
                    val_str = str(val)
                
                print(f"{config_key}={val_str} ({source})")
            
            print()
            return 0
        
        # UNSET: Remove a configuration value
        if unset:
            if not key:
                print("Error: --unset requires a key")
                return 1
            
            # For unset, validate key if it exists
            if key not in KNOWN_KEYS:
                print()
                print(f"Error: Unknown configuration key '{key}'")
                print()
                print("Valid configuration keys:")
                for k, desc in sorted(KNOWN_KEYS.items()):
                    print(f"  {k:<20} - {desc}")
                print()
                return 1
            
            # Load existing config
            if config_path.exists():
                current_config = self._load_json_file(config_path, f"{config_type} config")
            else:
                current_config = {}
            
            # Remove key if it exists (silently succeed if it doesn't)
            if key in current_config:
                del current_config[key]
                
                # Write back
                config_path.parent.mkdir(parents=True, exist_ok=True)
                with open(config_path, 'w') as f:
                    json.dump(current_config, f, indent=4)
                
                print(f"✓ Unset {key} in {config_type} config")
            # Else: silently succeed
            
            return 0
        
        # Validate key exists for GET and SET operations
        if key and key not in KNOWN_KEYS:
            print()
            print(f"Error: Unknown configuration key '{key}'")
            print()
            print("Valid configuration keys:")
            for k, desc in sorted(KNOWN_KEYS.items()):
                print(f"  {k:<20} - {desc}")
            print()
            return 1
        
        # GET: Retrieve a configuration value
        if key and value is None:
            # Load the merged config (uses existing 3-way merge)
            merged_config = self.load_config()
            
            if key in merged_config:
                val = merged_config[key]
                
                # Output pure value (no source info)
                if isinstance(val, dict):
                    print(json.dumps(val))
                else:
                    print(val)
            else:
                # Shouldn't happen since we check against KNOWN_KEYS
                print("")
            
            return 0
        
        # SET: Set a configuration value
        if key and value is not None:
            # Load existing config from target file
            if config_path.exists():
                current_config = self._load_json_file(config_path, f"{config_type} config")
            else:
                current_config = {}
            
            # Parse value (try to infer type)
            parsed_value = value
            
            # Try to parse as JSON for dicts/arrays
            if value.startswith('{') or value.startswith('['):
                try:
                    parsed_value = json.loads(value)
                except json.JSONDecodeError:
                    # Keep as string if not valid JSON
                    pass
            # Boolean conversion
            elif value.lower() in ('true', 'false'):
                parsed_value = value.lower() == 'true'
            # Number conversion
            elif value.isdigit():
                parsed_value = int(value)
            
            # Set the value
            current_config[key] = parsed_value
            
            # Create parent directory if needed
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write back
            with open(config_path, 'w') as f:
                json.dump(current_config, f, indent=4)
            
            print(f"✓ Set {key} = {value} in {config_type} config")
            return 0
        
        # If we get here, invalid usage
        print("Usage:")
        print("  git-pm config <key>                    # Get value")
        print("  git-pm config <key> <value>            # Set value (project)")
        print("  git-pm config --global <key> <value>   # Set value (user)")
        print("  git-pm config --unset <key>            # Unset value (project)")
        print("  git-pm config --unset --global <key>   # Unset value (user)")
        print("  git-pm config --list                   # List all settings")
        return 1
    
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
        "--no-gitignore",
        action="store_true",
        help="Skip automatic .gitignore management"
    )

    subparsers.add_parser("clean", help="Remove all installed packages")
    
    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a package from the project")
    remove_parser.add_argument("package", help="Package name to remove")
    remove_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Get or set configuration values")
    config_parser.add_argument("key", nargs="?", help="Configuration key (e.g., packages_dir, cache_dir)")
    config_parser.add_argument("value", nargs="?", help="Value to set")
    config_parser.add_argument(
        "--global",
        dest="is_global",
        action="store_true",
        help="Use user-level config (~/.git-pm/config)"
    )
    config_parser.add_argument(
        "--unset",
        action="store_true",
        help="Remove a configuration value"
    )
    config_parser.add_argument(
        "--list",
        dest="list_all",
        action="store_true",
        help="List all configuration values with sources"
    )
    
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
            manage_gitignore=not args.no_gitignore
        )
    elif args.command == "clean":
        return gpm.cmd_clean()
    elif args.command == "remove":
        return gpm.cmd_remove(args.package, auto_confirm=args.yes)
    elif args.command == "config":
        return gpm.cmd_config(
            key=args.key,
            value=args.value,
            is_global=args.is_global,
            unset=args.unset,
            list_all=args.list_all
        )
    elif args.command == "add":
        return gpm.cmd_add(args.name, args.repo, args.path, args.ref_type, args.ref_value)
    
    return 1


if __name__ == "__main__":
    sys.exit(main())