import os
import shutil
import pytest

brownie_available = shutil.which("brownie") is not None
@pytest.mark.skip_if(not brownie_available)
def test_brownie(make_tmpdir, run_command):
    tmpdirname = make_tmpdir
    
    initialize = ["brownie", "bake", "token"]
    test = ["crytic-compile", ".",  "--compile-force-framework", "brownie"]

    run_command(initialize, tmpdirname) 
    project_dir = os.path.join(tmpdirname,"token")
    assert os.path.isdir(project_dir)
    assert run_command(test, project_dir) == 0



