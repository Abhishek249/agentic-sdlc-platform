"""Code quality tools for linting and testing."""

import subprocess
from pathlib import Path
from typing import Any

from tools.base import Tool, ToolParameter, ToolExecutionError


class RunLinterTool(Tool):
    """
    Run ruff linter on Python files.
    
    Essential for PR review - catches style issues, unused imports, etc.
    """
    
    def __init__(self, repo_root: str = "/Users/ajain/pcp-repos"):
        super().__init__()
        self.name = "run_linter"
        self.description = (
            "Run ruff linter on Python files to check for code quality issues. "
            "Reports style violations, unused imports, complexity issues, etc. "
            "Use this to check if code follows best practices."
        )
        self.parameters = {
            "file_path": ToolParameter(
                type="string",
                description="Path to Python file or directory to lint (relative to repo root)",
                required=True
            )
        }
        self.repo_root = Path(repo_root)
        self.is_deterministic = True
    
    async def execute(self, file_path: str) -> str:
        """Run linter on file/directory."""
        try:
            target = Path(file_path)
            if not target.is_absolute():
                target = self.repo_root / target
            
            if not target.exists():
                raise ToolExecutionError(
                    self.name,
                    f"File or directory not found: {file_path}"
                )
            
            # Run ruff
            result = subprocess.run(
                ["ruff", "check", str(target), "--output-format=text"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Ruff returns non-zero if issues found, which is expected
            output = result.stdout
            
            if not output or "All checks passed" in output:
                return f"✅ No linting issues found in {file_path}"
            
            return f"Linting issues in {file_path}:\n\n{output}"
            
        except FileNotFoundError:
            raise ToolExecutionError(
                self.name,
                "Ruff not installed. Run: pip install ruff"
            )
        except subprocess.TimeoutExpired:
            raise ToolExecutionError(
                self.name,
                "Linter timed out"
            )
        except Exception as e:
            raise ToolExecutionError(
                self.name,
                f"Failed to run linter: {str(e)}"
            )


class RunTypeCheckerTool(Tool):
    """Run mypy type checker on Python files."""
    
    def __init__(self, repo_root: str = "/Users/ajain/pcp-repos"):
        super().__init__()
        self.name = "run_type_checker"
        self.description = (
            "Run mypy type checker on Python files to find type errors. "
            "Checks for type mismatches, missing type hints, etc."
        )
        self.parameters = {
            "file_path": ToolParameter(
                type="string",
                description="Path to Python file to type check",
                required=True
            )
        }
        self.repo_root = Path(repo_root)
        self.is_deterministic = True
    
    async def execute(self, file_path: str) -> str:
        """Run type checker."""
        try:
            target = Path(file_path)
            if not target.is_absolute():
                target = self.repo_root / target
            
            if not target.exists():
                raise ToolExecutionError(
                    self.name,
                    f"File not found: {file_path}"
                )
            
            result = subprocess.run(
                ["mypy", str(target)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout
            
            if "Success" in output:
                return f"✅ No type errors found in {file_path}"
            
            return f"Type checking results for {file_path}:\n\n{output}"
            
        except FileNotFoundError:
            return "⚠️ Mypy not installed. Skipping type check."
        except Exception as e:
            raise ToolExecutionError(
                self.name,
                f"Failed to run type checker: {str(e)}"
            )
