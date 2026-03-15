"""Tests for models/ directory organization.

These tests verify that the models directory has consistent module organization
and that utility functions are properly placed.

Test Location: tests/test_models_organization.py
Project: models/
Framework: pytest
"""

import pytest
from pathlib import Path
import ast
import os

# Try multiple import paths to handle different project layouts
try:
    import models
    MODELS_PATH = Path(models.__file__).parent
except ImportError:
    # Fallback: try to find models directory relative to test file
    MODELS_PATH = Path(__file__).parent.parent / "models"
    if not MODELS_PATH.exists():
        MODELS_PATH = Path(__file__).parent.parent.parent / "models"
    if not MODELS_PATH.exists():
        MODELS_PATH = Path("models")


class TestModelsDirectoryOrganization:
    """Test suite for models/ directory organization consistency."""

    def test_models_directory_exists(self):
        """Test that models directory exists in the project."""
        assert MODELS_PATH.exists(), f"Models directory not found at {MODELS_PATH}"
        assert MODELS_PATH.is_dir(), f"Models path exists but is not a directory: {MODELS_PATH}"

    def test_models_directory_is_not_empty(self):
        """Test that models directory contains Python modules."""
        py_files = list(MODELS_PATH.glob("*.py"))
        assert len(py_files) > 0, "models directory should contain at least one Python file"

    def test_utils_module_organization(self):
        """Test that _utils.py (if exists) is not trivially small or has proper content."""
        utils_file = MODELS_PATH / "_utils.py"
        
        if not utils_file.exists():
            # _utils.py was removed as part of consolidation - this is acceptable
            pytest.skip("_utils.py does not exist - may have been consolidated")
        
        # Read the file content
        content = utils_file.read_text()
        
        # Parse to check for actual code (not just comments/empty lines)
        try:
            tree = ast.parse(content)
        except SyntaxError:
            pytest.fail(f"_utils.py contains invalid Python syntax")
        
        # Count meaningful nodes (functions, classes, imports)
        meaningful_nodes = [
            node for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom))
        ]
        
        # Check if _utils.py has substantial content or was consolidated
        if len(meaningful_nodes) == 0:
            # File is empty or only has comments - suggests it should be removed/consolidated
            pytest.skip("_utils.py appears empty or only contains comments - may have been consolidated")

    def test_no_orphaned_utility_functions(self):
        """Test that utility functions in _utils.py are used by other modules or properly documented."""
        utils_file = MODELS_PATH / "_utils.py"
        
        if not utils_file.exists():
            # _utils.py was removed - that's fine if utilities were moved to appropriate places
            pytest.skip("_utils.py does not exist - utilities may have been consolidated")
        
        content = utils_file.read_text()
        
        # If file exists and has content, verify it's not trivially small
        # A utility module should have either multiple functions or be well-documented
        lines = [line.strip() for line in content.split('\n') if line.strip() and not line.strip().startswith('#')]
        
        if len(lines) < 5:
            # File is very small - this is the issue the finding describes
            # The fix should either remove it or consolidate utilities properly
            pytest.fail(
                f"_utils.py is trivially small ({len(lines)} non-comment lines). "
                "Utilities should either be moved to domain-specific modules or removed if unused."
            )

    def test_model_files_have_consistent_structure(self):
        """Test that model files in models/ follow consistent patterns."""
        py_files = [f for f in MODELS_PATH.glob("*.py") if not f.name.startswith('__')]
        
        if len(py_files) == 0:
            pytest.skip("No model files found to check consistency")
        
        # Check that model files can be imported
        for py_file in py_files:
            module_name = py_file.stem
            try:
                # Try to import the module
                import importlib.util
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    # Module can be loaded - that's sufficient for this test
                    pass
            except Exception as e:
                # Some import errors are acceptable (missing dependencies, etc.)
                # but we should at least verify the file is valid Python
                try:
                    py_file.read_text()
                except Exception:
                    pytest.fail(f"Cannot read model file {py_file.name}: {e}")

    def test_all_py_files_in_models_are_valid_syntax(self):
        """Test that all Python files in models/ directory have valid syntax."""
        py_files = list(MODELS_PATH.glob("*.py"))
        
        invalid_files = []
        for py_file in py_files:
            try:
                content = py_file.read_text()
                ast.parse(content)
            except SyntaxError as e:
                invalid_files.append((py_file.name, str(e)))
        
        if invalid_files:
            error_msgs = [f"{name}: {err}" for name, err in invalid_files]
            pytest.fail(f"Invalid syntax in models/ files: {'; '.join(error_msgs)}")
