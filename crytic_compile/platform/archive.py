import os
import json
from pathlib import Path
from . import standard

def is_archive(target):
    return Path(target).parts[-1].endswith("_export_archive.json")

def compile(crytic_compile, target, **kwargs):
    if isinstance(target, str) and os.path.isfile(target):
        with open(target, encoding='utf8') as f:
            loaded_json = json.load(f)
    else:
        loaded_json = json.loads(target)
    standard.load_from_compile(crytic_compile, loaded_json)

    crytic_compile._src_content = loaded_json['source_content']

def generate_archive_export(crytic_compile):
    output = standard.generate_standard_export(crytic_compile)
    output['source_content'] = crytic_compile.src_content

    target = crytic_compile.target
    target = "contracts" if os.path.isdir(target) else Path(target).parts[-1]
    target = f"{target}_export_archive.json"

    return output, target

def export(crytic_compile, **kwargs):
    # Obtain objects to represent each contract

    output, target = generate_archive_export(crytic_compile)

    export_dir = kwargs.get('export_dir', "crytic-compile")
    if export_dir:
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        path = os.path.join(export_dir, target)
        with open(path, 'w', encoding='utf8') as f:
            json.dump(output, f)

        return path
    return None

def is_dependency(_path):
    # handled by crytic_compile_dependencies
    return False

def _relative_to_short(relative):
    return relative
