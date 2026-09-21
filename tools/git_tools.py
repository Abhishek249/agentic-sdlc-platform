"""Git operation tools for code review."""

import subprocess
from pathlib import Path
from typing import Any

from tools.base import Tool, ToolParameter, ToolExecutionError


class GitDiffTool(Tool):
    """
    Get git diff for a branch or commit.
    
    Essential for PR review - shows what actually changed.
    """
    
    def __init__(self, repo_root: str = "/Users/ajain/pcp-repos"):
        super().__init__()
        self.name = "git_diff"
        self.description = (
            "Get the git diff showing what changed. "
            "Use this to see what code was added, modified, or deleted. "
            "Can compare branches, commits, or see uncommitted changes."
        )
        self.parameters = {
            "target": ToolParameter(
                type="string",
                description="What to diff against (e.g., 'origin/main', 'HEAD~1', or leave empty for uncommitted changes)",
                required=False
            ),
            "file_path": ToolParameter(
                type="string",
                description="Optional: specific file to diff (relative to repo root)",
                required=False
            )
        }
        self.repo_root = Path(repo_root)
        self.is_deterministic = True
    
    async def execute(self, target: str = "", file_path: str = "") -> str:
        """Get git diff."""
        try:
            # Build git command
            cmd = ["git", "diff"]
            
            if target:
                cmd.append(target)
            
            if file_path:
                cmd.append("--")
                cmd.append(file_path)
            
            # Execute git command
            result = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise ToolExecutionError(
                    self.name,
                    f"Git command failed: {result.stderr}"
                )
            
            diff_output = result.stdout
            
            if not diff_output:
                return "No changes found"
            
            # Limit output size (diffs can be huge)
            max_chars = 50000
            if len(diff_output) > max_chars:
                diff_output = diff_output[:max_chars] + f"\n... (truncated, {len(diff_output) - max_chars} chars omitted)"
            
            return diff_output
            
        except subprocess.TimeoutExpired:
            raise ToolExecutionError(
                self.name,
                "Git command timed out"
            )
        except Exception as e:
            raise ToolExecutionError(
                self.name,
                f"Failed to get diff: {str(e)}"
            )


class GitLogTool(Tool):
    """Get git commit history."""
    
    def __init__(self, repo_root: str = "/Users/ajain/pcp-repos"):
        super().__init__()
        self.name = "git_log"
        self.description = (
            "Get git commit history. Shows recent commits with messages. "
            "Useful for understanding what work has been done recently."
        )
        self.parameters = {
            "num_commits": ToolParameter(
                type="integer",
                description="Number of recent commits to show (default: 10)",
                required=False
            ),
            "file_path": ToolParameter(
                type="string",
                description="Optional: show commits that modified this file",
                required=False
            )
        }
        self.repo_root = Path(repo_root)
        self.is_deterministic = True
    
    async def execute(self, num_commits: int = 10, file_path: str = "") -> str:
        """Get git log."""
        try:
            cmd = [
                "git", "log",
                f"-{num_commits}",
                "--oneline",
                "--decorate"
            ]
            
            if file_path:
                cmd.extend(["--", file_path])
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                raise ToolExecutionError(
                    self.name,
                    f"Git command failed: {result.stderr}"
                )
            
            return result.stdout if result.stdout else "No commits found"
            
        except Exception as e:
            raise ToolExecutionError(
                self.name,
                f"Failed to get log: {str(e)}"
            )


class GitShowTool(Tool):
    """Show contents of a file at a specific commit."""
    
    def __init__(self, repo_root: str = "/Users/ajain/pcp-repos"):
        super().__init__()
        self.name = "git_show"
        self.description = (
            "Show the contents of a file at a specific commit. "
            "Useful for comparing old vs new versions."
        )
        self.parameters = {
            "commit": ToolParameter(
                type="string",
                description="Commit hash or reference (e.g., 'HEAD', 'HEAD~1', 'abc123')",
                required=True
            ),
            "file_path": ToolParameter(
                type="string",
                description="Path to the file (relative to repo root)",
                required=True
            )
        }
        self.repo_root = Path(repo_root)
        self.is_deterministic = True
    
    async def execute(self, commit: str, file_path: str) -> str:
        """Show file at commit."""
        try:
            cmd = ["git", "show", f"{commit}:{file_path}"]
            
            result = subprocess.run(
                cmd,
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                raise ToolExecutionError(
                    self.name,
                    f"Git command failed: {result.stderr}"
                )
            
            return result.stdout
            
        except Exception as e:
            raise ToolExecutionError(
                self.name,
                f"Failed to show file: {str(e)}"
            )
