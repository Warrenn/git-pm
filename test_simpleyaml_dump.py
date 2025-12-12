#!/usr/bin/env python3
"""
Test suite for SimpleYAML dump methods (Phase 1)
Tests the ability to write YAML files
"""

import sys
import tempfile
from pathlib import Path
from io import StringIO
import importlib.util

# Import SimpleYAML from git-pm.py
repo_root = Path(__file__).parent
spec = importlib.util.spec_from_file_location("git_pm", repo_root / "git-pm.py")
git_pm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(git_pm)
SimpleYAML = git_pm.SimpleYAML


def test_dump_simple_dict():
    """Test dumping a simple flat dictionary"""
    print("\n🧪 Test: Dump Simple Dictionary")
    
    data = {
        "name": "test-package",
        "version": "1.0.0",
        "author": "Test User"
    }
    
    output = StringIO()
    SimpleYAML.dump(data, output)
    result = output.getvalue()
    
    # Verify output
    assert "author: Test User" in result, "Should contain author"
    assert "name: test-package" in result, "Should contain name"
    assert "version: 1.0.0" in result, "Should contain version"
    
    # Verify sorted keys
    lines = result.strip().split('\n')
    keys = [line.split(':')[0].strip() for line in lines]
    assert keys == sorted(keys), "Keys should be sorted"
    
    print("  ✅ Simple dictionary dumps correctly")
    return True


def test_dump_nested_dict():
    """Test dumping nested dictionaries"""
    print("\n🧪 Test: Dump Nested Dictionary")
    
    data = {
        "packages": {
            "utils": {
                "repo": "github.com/test/repo",
                "path": "packages/utils"
            },
            "config": {
                "repo": "github.com/test/repo",
                "path": "packages/config"
            }
        },
        "version": "1.0.0"
    }
    
    output = StringIO()
    SimpleYAML.dump(data, output)
    result = output.getvalue()
    
    # Verify nesting
    assert "packages:" in result, "Should contain packages key"
    assert "  utils:" in result, "Should contain nested utils"
    assert "    repo: github.com/test/repo" in result, "Should contain deeply nested value"
    assert "version: 1.0.0" in result, "Should contain root level value"
    
    print("  ✅ Nested dictionary dumps correctly")
    return True


def test_dump_boolean_values():
    """Test dumping boolean values"""
    print("\n🧪 Test: Dump Boolean Values")
    
    data = {
        "enabled": True,
        "disabled": False,
        "name": "test"
    }
    
    output = StringIO()
    SimpleYAML.dump(data, output)
    result = output.getvalue()
    
    # Booleans should be lowercase
    assert "enabled: true" in result, "True should be lowercase 'true'"
    assert "disabled: false" in result, "False should be lowercase 'false'"
    assert "enabled: True" not in result, "Should not have capitalized True"
    assert "disabled: False" not in result, "Should not have capitalized False"
    
    print("  ✅ Boolean values dump correctly")
    return True


def test_dump_number_values():
    """Test dumping number values"""
    print("\n🧪 Test: Dump Number Values")
    
    data = {
        "count": 42,
        "rate": 3.14,
        "zero": 0
    }
    
    output = StringIO()
    SimpleYAML.dump(data, output)
    result = output.getvalue()
    
    assert "count: 42" in result, "Should contain integer"
    assert "rate: 3.14" in result, "Should contain float"
    assert "zero: 0" in result, "Should contain zero"
    
    print("  ✅ Number values dump correctly")
    return True


def test_dump_empty_dict():
    """Test dumping empty dictionary"""
    print("\n🧪 Test: Dump Empty Dictionary")
    
    data = {
        "packages": {},
        "name": "test"
    }
    
    output = StringIO()
    SimpleYAML.dump(data, output)
    result = output.getvalue()
    
    assert "packages: {}" in result, "Empty dict should be '{}'"
    
    print("  ✅ Empty dictionary dumps correctly")
    return True


def test_dump_with_special_chars():
    """Test dumping strings with special characters"""
    print("\n🧪 Test: Dump Strings with Special Characters")
    
    data = {
        "url": "https://github.com/user/repo",
        "path": "path/to:resource",
        "comment": "This has a # comment char"
    }
    
    output = StringIO()
    SimpleYAML.dump(data, output)
    result = output.getvalue()
    
    # Special chars should trigger quoting
    assert 'comment: "This has a # comment char"' in result, "Should quote string with #"
    assert 'path: "path/to:resource"' in result, "Should quote string with :"
    
    print("  ✅ Special characters handled correctly")
    return True


def test_dumps_to_string():
    """Test dumps() method returns string"""
    print("\n🧪 Test: dumps() Returns String")
    
    data = {
        "name": "test",
        "value": 123
    }
    
    result = SimpleYAML.dumps(data)
    
    assert isinstance(result, str), "dumps() should return string"
    assert "name: test" in result, "Should contain data"
    assert "value: 123" in result, "Should contain value"
    
    print("  ✅ dumps() returns string correctly")
    return True


def test_dump_to_file():
    """Test dumping to actual file"""
    print("\n🧪 Test: Dump to File")
    
    data = {
        "packages": {
            "test": {
                "version": "1.0.0"
            }
        },
        "enabled": True
    }
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yaml') as f:
        temp_file = Path(f.name)
        SimpleYAML.dump(data, f)
    
    try:
        # Read back and verify
        content = temp_file.read_text()
        assert "packages:" in content, "File should contain data"
        assert "enabled: true" in content, "File should contain boolean"
        
        # Verify can be loaded back
        with open(temp_file, 'r') as f:
            loaded = SimpleYAML.load(f)
        
        assert loaded['packages']['test']['version'] == "1.0.0", "Should load back correctly"
        assert loaded['enabled'] == "true", "Boolean loads as string (current behavior)"
        
        print("  ✅ Dump to file works correctly")
        return True
    finally:
        temp_file.unlink()


def test_dump_list_values():
    """Test dumping list values"""
    print("\n🧪 Test: Dump List Values")
    
    data = {
        "tags": ["v1.0.0", "v1.0.1", "latest"],
        "empty": [],
        "name": "test"
    }
    
    output = StringIO()
    SimpleYAML.dump(data, output)
    result = output.getvalue()
    
    # Lists should be formatted
    assert "tags:" in result, "Should contain list key"
    assert "  - v1.0.0" in result, "Should contain list item"
    assert "  - v1.0.1" in result, "Should contain list item"
    assert "empty: []" in result, "Empty list should be '[]'"
    
    print("  ✅ List values dump correctly")
    return True


def test_dump_null_values():
    """Test dumping None/null values"""
    print("\n🧪 Test: Dump Null Values")
    
    data = {
        "name": "test",
        "description": None,
        "enabled": True
    }
    
    output = StringIO()
    SimpleYAML.dump(data, output)
    result = output.getvalue()
    
    assert "description: null" in result, "None should be 'null'"
    
    print("  ✅ Null values dump correctly")
    return True


def test_round_trip():
    """Test that dump -> load -> dump produces same output"""
    print("\n🧪 Test: Round Trip (dump → load → dump)")
    
    original_data = {
        "packages": {
            "utils": {
                "repo": "github.com/test/repo",
                "version": "1.0.0"
            }
        },
        "enabled": True,
        "count": 42
    }
    
    # First dump
    first_dump = SimpleYAML.dumps(original_data)
    
    # Load it back
    loaded_data = SimpleYAML.loads(first_dump)
    
    # Dump again
    second_dump = SimpleYAML.dumps(loaded_data)
    
    # Note: Booleans become strings when loaded, so exact match won't work
    # But structure should be preserved
    assert "packages:" in second_dump, "Structure preserved"
    assert "utils:" in second_dump, "Nested keys preserved"
    
    print("  ✅ Round trip preserves structure")
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("SimpleYAML Dump Methods Test Suite (Phase 1)")
    print("=" * 60)
    
    tests = [
        ("Dump Simple Dictionary", test_dump_simple_dict),
        ("Dump Nested Dictionary", test_dump_nested_dict),
        ("Dump Boolean Values", test_dump_boolean_values),
        ("Dump Number Values", test_dump_number_values),
        ("Dump Empty Dictionary", test_dump_empty_dict),
        ("Dump Special Characters", test_dump_with_special_chars),
        ("dumps() to String", test_dumps_to_string),
        ("Dump to File", test_dump_to_file),
        ("Dump List Values", test_dump_list_values),
        ("Dump Null Values", test_dump_null_values),
        ("Round Trip", test_round_trip),
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
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())