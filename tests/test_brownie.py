import os
import shutil
import tempfile
import subprocess
import pytest
from typing import List

# cmd = [sys.executable, "-m", "pip", "install", "eth-brownie"]

import logging
LOGGER = logging.getLogger(__name__)

def run(command: List[str], cwd: str) -> int:
    process = subprocess.run(
                        command,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        executable=shutil.which(command[0]),
                        cwd=cwd,
                        check=True
                    )
    LOGGER.info(process.stdout.decode("utf-8"))
    LOGGER.error(process.stderr.decode("utf-8"))
    return process.returncode

brownie_available = shutil.which("brownie") is not None
@pytest.mark.skip_if(not brownie_available)
def test_brownie():
    initialize = ["brownie", "bake", "token"]
    test = ["crytic-compile", ".",  "--compile-force-framework", "brownie"]

    with tempfile.TemporaryDirectory() as tmpdirname:

        run(initialize, tmpdirname) 

        run(test,os.path.join(tmpdirname,"token")) == 0


