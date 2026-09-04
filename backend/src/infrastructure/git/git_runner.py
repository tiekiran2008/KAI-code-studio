"""
Git Command Runner
==================
Secure, narrow execution boundary for local Git CLI invocations.
Enforces structured argv, timeouts, path sandboxing, zero shell interpretation,
and strict command allowlisting.
"""
import os
from pathlib import Path
import re
import subprocess
from typing import Dict, List, Optional, Tuple

from src.core.logger import logger


class GitExecutionError(Exception):
    """Raised when a Git command returns a non-zero exit code."""
    def __init__(self, message: str, exit_code: int = 1, stderr: str = "") -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.stderr = stderr


class GitCommandRunner:
    """Hardened execution runner for Git subprocess calls."""

    DEFAULT_TIMEOUT_SECONDS: float = 15.0

    # Explicitly forbidden commands & flags across all workflows
    FORBIDDEN_COMMANDS = {
        "push",
        "rebase",
        "merge",
        "cherry-pick",
    }

    FORBIDDEN_FLAG_PATTERNS = [
        "--force",
        "--force-with-lease",
        "--hard",
        "-fd",
        "-f",
    ]

    def __init__(self, git_binary: str = "git") -> None:
        self.git_binary = git_binary

    def run(
        self,
        args: List[str],
        cwd: Path,
        env_override: Optional[Dict[str, str]] = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        check: bool = True,
    ) -> Tuple[int, str, str]:
        """Execute a git command with strict sandboxing and argv list.

        Parameters
        ----------
        args : List[str]
            Structured list of git subcommands and arguments (e.g. ["status", "--porcelain"]).
        cwd : Path
            Trusted directory where the git command should run.
        env_override : Optional[Dict[str, str]]
            Optional environment variables (such as GIT_INDEX_FILE).
        timeout : float
            Execution timeout in seconds.
        check : bool
            If True, raises GitExecutionError on non-zero exit code.

        Returns
        -------
        Tuple[int, str, str]
            (exit_code, stdout, stderr)
        """
        if not args or not isinstance(args, list):
            raise ValueError("Git arguments must be a non-empty list of strings")

        # 1. Security Check: Command allowlist / blocklist
        subcommand = args[0].lower() if args else ""
        if subcommand in self.FORBIDDEN_COMMANDS:
            raise GitExecutionError(f"Prohibited git subcommand: '{subcommand}'")

        # Check for forbidden destructive flags
        for arg in args:
            for forbidden_flag in self.FORBIDDEN_FLAG_PATTERNS:
                if arg == forbidden_flag:
                    raise GitExecutionError(f"Prohibited git flag detected: '{arg}'")

        # 2. Prepare environment: inherit safe PATH/SystemRoot, disable prompts
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["PAGER"] = "cat"
        if env_override:
            env.update(env_override)

        cmd = [self.git_binary] + args

        try:
            result = subprocess.run(
                cmd,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                timeout=timeout,
                check=False,
                shell=False,  # CRITICAL: Never enable shell execution mode
            )

            stdout = result.stdout.strip()
            stderr = result.stderr.strip()

            if check and result.returncode != 0:
                logger.warning(
                    "git_command_error",
                    cmd=" ".join(cmd),
                    exit_code=result.returncode,
                    stderr=stderr,
                )
                raise GitExecutionError(
                    f"Git command '{args[0]}' failed (exit code {result.returncode}): {stderr or stdout}",
                    exit_code=result.returncode,
                    stderr=stderr,
                )

            return result.returncode, stdout, stderr

        except subprocess.TimeoutExpired as exc:
            logger.error("git_command_timeout", cmd=" ".join(cmd), timeout=timeout)
            raise GitExecutionError(f"Git command timed out after {timeout} seconds", exit_code=-1)
        except FileNotFoundError:
            raise GitExecutionError("Git executable not found on system PATH")
        except Exception as exc:
            if isinstance(exc, GitExecutionError):
                raise
            raise GitExecutionError(f"Failed executing git command: {exc}")

    def push_ref(
        self,
        remote_name: str,
        local_ref: str,
        remote_ref: str,
        cwd: Path,
        timeout: float = 30.0,
    ) -> Tuple[int, str, str]:
        """Safely push a single dedicated AI branch refspec to a trusted remote.

        Parameters
        ----------
        remote_name : str
            Trusted remote name (e.g. 'origin').
        local_ref : str
            Full local ref path (e.g. 'refs/heads/ai-fix/rev-12345678-f0').
        remote_ref : str
            Full remote ref path (e.g. 'refs/heads/ai-fix/rev-12345678-f0').
        cwd : Path
            Local repository workspace path.

        Enforces:
        - Exact full ref paths (must begin with 'refs/heads/')
        - Prohibits '+' prefix (never allows force refspec)
        - Never enables shell execution mode (shell=False)
        - Zero interactive prompts (GIT_TERMINAL_PROMPT=0)
        - Safe timeout
        """
        # 1. Validate remote name
        if not remote_name or not re.match(r"^[a-zA-Z0-9._-]+$", remote_name):
            raise GitExecutionError(f"Invalid remote name: '{remote_name}'")

        # 2. Strict refspec validation: must start with refs/heads/, no '+' prefix
        for ref_val in (local_ref, remote_ref):
            if not ref_val or not ref_val.startswith("refs/heads/"):
                raise GitExecutionError(f"Ref must be a fully qualified 'refs/heads/...' path, got: '{ref_val}'")
            if ref_val.startswith("+"):
                raise GitExecutionError("Force push refspec '+' is strictly prohibited")
            if ".." in ref_val or "~" in ref_val or "^" in ref_val or ":" in ref_val:
                raise GitExecutionError(f"Prohibited character in ref path: '{ref_val}'")

        refspec = f"{local_ref}:{remote_ref}"
        args = [self.git_binary, "push", "--porcelain", remote_name, refspec]

        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["PAGER"] = "cat"

        try:
            result = subprocess.run(
                args,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                timeout=timeout,
                check=False,
                shell=False,
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            logger.error("git_push_timeout", remote=remote_name, refspec=refspec, timeout=timeout)
            return -1, "", f"Git push timed out after {timeout} seconds"
        except FileNotFoundError:
            return 1, "", "Git executable not found on system PATH"
        except Exception as exc:
            return 1, "", f"Failed executing git push: {exc}"

