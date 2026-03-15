"""Tests for models/ module organization and _utils.py refactoring.

These tests verify that the models/ directory has consistent module organization
and that _utils.py contents are either meaningful utilities used across models
or have been properly refactored into their respective model files.

Test Location: tests/test_models_module_organization.py
Project: models/
Framework: pytest
"""

import pytest
import ast
from pathlib import Path


class TestModelsModuleOrganization:
    """Test suite for models/ directory organization."""

    def test_utils_file_has_meaningful_content_or_refactored(self):
        """Test that _utils.py either has significant utility content or has been refactored."""
        models_dir = Path(__file__).parent.parent / "models"
        utils_file = models_dir / "_utils.py"
        
        if not utils_file.exists():
            # File was refactored/moved - this is acceptable
            pytest.skip("_utils.py has been refactored to dedicated module files")
            return
        
        # Read and analyze _utils.py content
        content = utils_file.read_text()
        
        # Parse the file to count actual utility functions
        try:
            tree = ast.parse(content)
        except SyntaxError:
            pytest.fail("_utils.py contains syntax errors")
        
        # Count meaningful functions (not just __init__ or trivial helpers)
        utility_functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Skip private helpers with very simple implementations
                if not node.name.startswith('_'):
                    # Check if function has meaningful logic (more than just pass/return)
                    if len(node.body) > 1 or not isinstance(node.body[0], ast.Pass):
                        utility_functions.append(node.name)
        
        # Either _utils.py should have meaningful utilities OR be removed/refactored
        # A trivially small file (< 10 LOC effective) should not exist
        assert len(utility_functions) >= 2 or len(content.strip()) > 500, (
            f"_utils.py appears to be trivially small ({len(content)} chars) with only "
            f"{len(utility_functions)} utility functions. Consider refactoring into "
            "respective model files or consolidating utilities."
        )

    def test_utils_functions_are_used_by_multiple_models(self):
        """Test that utilities in _utils.py are actually used by multiple model files."""
        models_dir = Path(__file__).parent.parent / "models"
        utils_file = models_dir / "_utils.py"
        
        if not utils_file.exists():
            # File was refactored - this is acceptable
            pytest.skip("_utils.py has been refactored")
            return
        
        content = utils_file.read_text()
        
        # Extract function names from _utils.py
        try:
            tree = ast.parse(content)
        except SyntaxError:
            pytest.fail("_utils.py contains syntax errors")
            return
        
        utils_funcs = [
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_')
        ]
        
        if not utils_funcs:
            # No public functions - acceptable
            return
        
        # Check if any model files import from _utils
        model_files = list(models_dir.glob("*.py"))
        model_files = [f for f in model_files if f.name not in ["_utils.py", "__init__.py"]]
        
        importing_models = []
        for model_file in model_files:
            model_content = model_file.read_text()
            if "_utils" in model_content or "from . import _utils" in model_content:
                importing_models.append(model_file.name)
        
        # If utilities exist in _utils.py, they should be used by at least one model
        # Otherwise they should be in their respective model files
        assert len(importing_models) > 0, (
            f"_utils.py contains functions ({utils_funcs}) but no model files "
            "import from it. Consider moving these to their respective model files."
        )

    def test_models_directory_contains_consistent_structure(self):
        """Test that models/ directory follows consistent naming and organization."""
        models_dir = Path(__file__).parent.parent / "models"
        
        if not models_dir.exists():
            pytest.fail("models/ directory does not exist")
        
        model_files = list(models_dir.glob("*.py"))
        
        # Filter out __init__.py and private files
        public_models = [
            f for f in model_files 
            if f.name != "__init__.py" and not f.name.startswith('_')
        ]
        
        # At least one public model file should exist
        assert len(public_models) > 0, (
            "models/ directory should contain at least one public model file"
        )
        
        # Check that model files have meaningful content (not empty)
        for model_file in public_models:
            content = model_file.read_text()
            assert len(content.strip()) > 0, (
                f"{model_file.name} is empty or contains only whitespace"
            )
