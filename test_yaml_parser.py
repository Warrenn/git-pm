#!/usr/bin/env python3
"""Test SimpleYAML parser with empty dictionaries"""

import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Import git-pm
import importlib.util
spec = importlib.util.spec_from_file_location("gitpm", Path(__file__).parent / "git-pm.py")
gitpm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gitpm)

SimpleYAML = gitpm.SimpleYAML

def test_empty_dict():
    """Test parsing packages: {}"""
    yaml_text = """packages: {}"""
    result = SimpleYAML.loads(yaml_text)
    print(f"Test 1 - Empty inline dict:")
    print(f"  Input: {yaml_text}")
    print(f"  Result: {result}")
    print(f"  Type of packages: {type(result.get('packages')).__name__}")
    assert isinstance(result.get('packages'), dict), "packages should be a dict"
    assert result.get('packages') == {}, "packages should be empty dict"
    print("  ✅ PASS\n")

def test_nested_empty_dict():
    """Test parsing nested structure with empty dict"""
    yaml_text = """packages:
  base:
    repo: github.com/test/repo
    path: packages/base
    ref:
      type: tag
      value: v1.0.0
dependencies: {}"""
    result = SimpleYAML.loads(yaml_text)
    print(f"Test 2 - Nested with empty dict:")
    print(f"  Result: {result}")
    print(f"  Type of dependencies: {type(result.get('dependencies')).__name__}")
    assert isinstance(result.get('dependencies'), dict), "dependencies should be a dict"
    assert result.get('dependencies') == {}, "dependencies should be empty dict"
    print("  ✅ PASS\n")

def test_file_parsing():
    """Test parsing from file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("packages: {}\n")
        f.write("version: 1.0\n")
        temp_path = f.name
    
    try:
        with open(temp_path, 'r') as f:
            result = SimpleYAML.load(f)
        
        print(f"Test 3 - File parsing:")
        print(f"  Result: {result}")
        print(f"  Type of packages: {type(result.get('packages')).__name__}")
        assert isinstance(result.get('packages'), dict), "packages should be a dict"
        assert result.get('packages') == {}, "packages should be empty dict"
        assert result.get('version') == '1.0', "version should be 1.0"
        print("  ✅ PASS\n")
    finally:
        Path(temp_path).unlink()

def test_empty_list():
    """Test parsing tags: []"""
    yaml_text = """tags: []
name: test"""
    result = SimpleYAML.loads(yaml_text)
    print(f"Test 4 - Empty inline list:")
    print(f"  Input: {yaml_text}")
    print(f"  Result: {result}")
    print(f"  Type of tags: {type(result.get('tags')).__name__}")
    assert isinstance(result.get('tags'), list), "tags should be a list"
    assert result.get('tags') == [], "tags should be empty list"
    print("  ✅ PASS\n")

def test_real_world_manifest():
    """Test real git-pm.yaml format"""
    yaml_text = """packages:
  utils:
    repo: github.com/company/monorepo
    path: packages/utils
    ref:
      type: tag
      value: v1.0.0
  base:
    repo: github.com/company/monorepo
    path: packages/base
    ref:
      type: branch
      value: main"""
    result = SimpleYAML.loads(yaml_text)
    print(f"Test 5 - Real manifest:")
    print(f"  Result: {result}")
    assert isinstance(result.get('packages'), dict), "packages should be a dict"
    assert len(result.get('packages')) == 2, "should have 2 packages"
    assert 'utils' in result.get('packages'), "should have utils"
    assert 'base' in result.get('packages'), "should have base"
    print("  ✅ PASS\n")

if __name__ == "__main__":
    print("=" * 60)
    print("Testing SimpleYAML parser with empty dictionaries")
    print("=" * 60 + "\n")
    
    try:
        test_empty_dict()
        test_nested_empty_dict()
        test_file_parsing()
        test_empty_list()
        test_real_world_manifest()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
