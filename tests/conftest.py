import shutil
import tempfile
import subprocess
import pytest
from typing import List

@pytest.fixture
def make_tmpdir():
    with tempfile.TemporaryDirectory() as tmpdirname:
        yield tmpdirname


import logging
LOGGER = logging.getLogger(__name__)

@pytest.fixture
def run_command():
    def _run(command: List[str], cwd: str) -> int:
        executable = shutil.which(command[0])
        assert executable 
        process = subprocess.run(
                            command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            executable=executable,
                            cwd=cwd,
                            check=True
                        )
        LOGGER.info(process.stdout.decode("utf-8"))
        LOGGER.error(process.stderr.decode("utf-8"))
        return process.returncode
    return _run