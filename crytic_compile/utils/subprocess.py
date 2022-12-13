import logging
import os
from pathlib import Path
import shutil
import subprocess
from typing import Dict, List

LOGGER = logging.getLogger("CryticCompile")


def run(
    cmd: List[str],
    cwd: os.PathLike | None = None,
    extra_env: Dict[str, str] | None = None,
    **kwargs,
) -> subprocess.CompletedProcess | None:
    """
    Execute a command in a cross-platform compatible way.

    Args:
        cmd (List[str]): Command to run
        cwd (PathLike): Working directory to run the command in
        extra_env (Dict[str, str]): extra environment variables to define for the execution
        **kwargs: optional arguments passed to `subprocess.run`

    Returns:
        CompletedProcess: If the execution succeeded
        None: if there was a problem executing
    """
    subprocess_cwd = Path(os.getcwd() if cwd is None else cwd).resolve()
    subprocess_env = None if extra_env is None else dict(os.environ, extra_env)
    subprocess_exe = shutil.which(cmd[0])

    if subprocess_exe is None:
        LOGGER.error("Cannot execute `%s`, is it installed and in PATH?", cmd[0])
        return None

    LOGGER.info(
        "'%s' running (wd: %s)",
        " ".join(cmd),
        subprocess_cwd,
    )

    try:
        return subprocess.run(
            cmd, cwd=subprocess_cwd, executable=subprocess_exe, env=subprocess_env, **kwargs
        )
    except FileNotFoundError:
        LOGGER.error("Could not execute `%s`, is it installed and in PATH?", cmd[0])
    except OSError:
        LOGGER.error("OS error executing:", exc_info=1)

    return None