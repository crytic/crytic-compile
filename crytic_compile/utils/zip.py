import json
from zipfile import ZipFile
from crytic_compile.platform.archive import generate_archive_export

def load_from_zip(target):
    from crytic_compile.crytic_compile import CryticCompile
    compilations = []
    with ZipFile(target, 'r') as f:
        for project in f.namelist():
            compilations.append(CryticCompile(f.read(project), compile_force_framework="archive"))

    return compilations

def save_to_zip(crytic_compiles, zipfile):
    with ZipFile(zipfile, 'w') as f:
        for crytic_compile in crytic_compiles:
            output, target_name = generate_archive_export(crytic_compile)
            f.writestr(target_name, json.dumps(output))
