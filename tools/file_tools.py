"""File operation tools for agents."""

import os
from pathlib import Path
from typing import Any

from tools.base import Tool, ToolParameter, ToolExecutionError


class ReadFileTool(Tool):
    """
    Tool for reading file contents.
    
    This is one of the most basic but essential tools - agents need to
    read files to understand code, configs, docs, etc.
    """
    
    def __init__(self, workspace_root: str = "/Users/ajain/pcp-repos"):
        super().__init__()
        self.name = "read_file"
        self.description = (
            "Read the entire contents of a file from the filesystem. "
            "Use this to examine code, configuration files, documentation, or any text file. "
            "Provide the full path to the file."
        )
        self.parameters = {
            "path": ToolParameter(
                type="string",
                description="Absolute or relative path to the file to read (e.g., 'pcubed-pro-api/app/main.py')",
                required=True
            )
        }
        self.workspace_root = Path(workspace_root)
        self.is_deterministic = True  # Same file, same content (usually)
    
    async def execute(self, path: str) -> str:
        """
        Read and return file contents.
        
        Args:
            path: File path (relative to workspace or absolute)
            
        Returns:
            File contents as string
            
        Raises:
            ToolExecutionError: If file doesn't exist or can't be read
        """
        try:
            # Convert to absolute path if relative
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = self.workspace_root / file_path
            
            # Security check - ensure file is within workspace
            if not self._is_safe_path(file_path):
                raise ToolExecutionError(
                    self.name,
                    f"Access denied: {path} is outside workspace"
                )
            
            # Read file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return content
            
        except FileNotFoundError:
            raise ToolExecutionError(
                self.name,
                f"File not found: {path}"
            )
        except PermissionError:
            raise ToolExecutionError(
                self.name,
                f"Permission denied: {path}"
            )
        except UnicodeDecodeError:
            raise ToolExecutionError(
                self.name,
                f"Cannot read file (not text): {path}"
            )
        except Exception as e:
            raise ToolExecutionError(
                self.name,
                f"Failed to read {path}: {str(e)}"
            )
    
    def _is_safe_path(self, path: Path) -> bool:
        """
        Check if path is safe (within workspace).
        
        This prevents agents from reading sensitive files like /etc/passwd
        """
        try:
            # Resolve symlinks and relative paths
            resolved = path.resolve()
            workspace = self.workspace_root.resolve()
            
            # Check if file is within workspace
            return resolved.is_relative_to(workspace)
        except (ValueError, RuntimeError):
            return False


class WriteFileTool(Tool):
    """
    Tool for writing file contents.
    
    ⚠️ DANGEROUS - This tool can modify files!
    Use with caution in production.
    """
    
    def __init__(self, workspace_root: str = "/Users/ajain/pcp-repos"):
        super().__init__()
        self.name = "write_file"
        self.description = (
            "Write content to a file. Creates the file if it doesn't exist, "
            "overwrites if it does. Use this to create or update files."
        )
        self.parameters = {
            "path": ToolParameter(
                type="string",
                description="Path to the file to write",
                required=True
            ),
            "content": ToolParameter(
                type="string",
                description="Content to write to the file",
                required=True
            )
        }
        self.workspace_root = Path(workspace_root)
        self.is_deterministic = False  # Writing changes state
    
    async def execute(self, path: str, content: str) -> str:
        """Write content to file."""
        try:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = self.workspace_root / file_path
            
            # Security check
            if not self._is_safe_path(file_path):
                raise ToolExecutionError(
                    self.name,
                    f"Access denied: {path} is outside workspace"
                )
            
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"Successfully wrote {len(content)} characters to {path}"
            
        except Exception as e:
            raise ToolExecutionError(
                self.name,
                f"Failed to write {path}: {str(e)}"
            )
    
    def _is_safe_path(self, path: Path) -> bool:
        """Check if path is safe."""
        try:
            resolved = path.resolve()
            workspace = self.workspace_root.resolve()
            return resolved.is_relative_to(workspace)
        except (ValueError, RuntimeError):
            return False


class ListFilesTool(Tool):
    """
    Tool for listing files in a directory.
    
    Useful for agents to explore the codebase structure.
    """
    
    def __init__(self, workspace_root: str = "/Users/ajain/pcp-repos"):
        super().__init__()
        self.name = "list_files"
        self.description = (
            "List all files and directories in a given path. "
            "Use this to explore the codebase structure."
        )
        self.parameters = {
            "path": ToolParameter(
                type="string",
                description="Directory path to list (default: current directory)",
                required=False
            ),
            "pattern": ToolParameter(
                type="string",
                description="Optional glob pattern to filter files (e.g., '*.py', '**/*.ts')",
                required=False
            )
        }
        self.workspace_root = Path(workspace_root)
        self.is_deterministic = True
    
    async def execute(self, path: str = ".", pattern: str | None = None) -> str:
        """List files in directory."""
        try:
            dir_path = Path(path)
            if not dir_path.is_absolute():
                dir_path = self.workspace_root / dir_path
            
            if not dir_path.exists():
                raise ToolExecutionError(
                    self.name,
                    f"Directory not found: {path}"
                )
            
            if not dir_path.is_dir():
                raise ToolExecutionError(
                    self.name,
                    f"Not a directory: {path}"
                )
            
            # List files
            if pattern:
                files = sorted(dir_path.glob(pattern))
            else:
                files = sorted(dir_path.iterdir())
            
            # Format output
            result = []
            for file in files[:100]:  # Limit to 100 files
                rel_path = file.relative_to(self.workspace_root)
                file_type = "📁" if file.is_dir() else "📄"
                result.append(f"{file_type} {rel_path}")
            
            if len(files) > 100:
                result.append(f"... and {len(files) - 100} more files")
            
            return "\n".join(result) if result else "No files found"
            
        except Exception as e:
            raise ToolExecutionError(
                self.name,
                f"Failed to list {path}: {str(e)}"
            )
