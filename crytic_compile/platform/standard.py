# Standard crytic-compile export
import os
import json
from pathlib import Path

from crytic_compile.compiler.compiler import CompilerVersion
from crytic_compile.utils.naming import Filename

def is_standard(target):
    return Path(target).parts[-1].endswith("_export.json")

def generate_standard_export(crytic_compile):
    contracts = dict()
    for contract_name in crytic_compile.contracts_names:
        filename = crytic_compile.filename_of_contract(contract_name)
        librairies = crytic_compile.libraries_names_and_patterns(contract_name)
        contracts[contract_name] = {
            'abi': crytic_compile.abi(contract_name),
            'bin': crytic_compile.bytecode_init(contract_name),
            'bin-runtime': crytic_compile.bytecode_runtime(contract_name),
            'srcmap': ";".join(crytic_compile.srcmap_init(contract_name)),
            'srcmap-runtime': ";".join(crytic_compile.srcmap_runtime(contract_name)),
            'filenames': {
                'absolute': filename.absolute,
                'used': filename.used,
                'short': filename.short,
                'relative': filename.relative
            },
            'libraries': dict(librairies) if librairies else dict(),
            'is_dependency': crytic_compile._platform.is_dependency(filename.absolute)
        }

    # Create our root object to contain the contracts and other information.
    output = {
        'asts': crytic_compile._asts,
        'contracts': contracts,
        'compiler': {
            'compiler': crytic_compile._compiler_version.compiler,
            'version': crytic_compile._compiler_version.version,
            'optimized': crytic_compile._compiler_version.optimized,
        },
        'working_dir': str(crytic_compile._working_dir),
        'type': int(crytic_compile._type)
    }
    return output

def export(crytic_compile, **kwargs):
    # Obtain objects to represent each contract

    output = generate_standard_export(crytic_compile)

    export_dir = kwargs.get('export_dir', "crytic-compile")
    if export_dir:
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        target = crytic_compile.target
        target = "contracts" if os.path.isdir(target) else Path(target).parts[-1]

        path = os.path.join(export_dir, f"{target}.json")
        with open(path, 'w', encoding='utf8') as f:
            json.dump(output, f)

        return path
    return None

def compile(crytic_compile, target, **kwargs):
    with open(target, encoding='utf8') as f:
        loaded_json = json.load(f)
    load_from_compile(crytic_compile, loaded_json)

def load_from_compile(crytic_compile, loaded_json):
    crytic_compile._asts = loaded_json['asts']
    crytic_compile._compiler_version = CompilerVersion(compiler=loaded_json['compiler']['compiler'],
                                             version=loaded_json['compiler']['version'],
                                             optimized=loaded_json['compiler']['optimized'])
    for contract_name, contract in loaded_json['contracts'].items():
        crytic_compile._contracts_name.add(contract_name)
        filename = Filename(absolute=contract['filenames']['absolute'],
                            relative=contract['filenames']['relative'],
                            short=contract['filenames']['short'],
                            used=contract['filenames']['used'])
        crytic_compile._contracts_filenames[contract_name] = filename

        crytic_compile._abis[contract_name] = contract['abi']
        crytic_compile._init_bytecodes[contract_name] = contract['bin']
        crytic_compile._runtime_bytecodes[contract_name] = contract['bin-runtime']
        crytic_compile._srcmaps[contract_name] = contract['srcmap'].split(';')
        crytic_compile._srcmaps_runtime[contract_name] = contract['srcmap-runtime'].split(';')
        crytic_compile._libraries[contract_name] = contract['libraries']

        if contract['is_dependency']:
            crytic_compile._is_dependencies.add(filename.absolute)
            crytic_compile._is_dependencies.add(filename.relative)
            crytic_compile._is_dependencies.add(filename.short)
            crytic_compile._is_dependencies.add(filename.used)


    # Set our filenames
    crytic_compile._filenames = set(crytic_compile._contracts_filenames.values())

    crytic_compile._working_dir = loaded_json['working_dir']
    crytic_compile._type = loaded_json['type']


def is_dependency(filename):
    # handled by crytic_compile_dependencies
    return False

def _relative_to_short(relative):
    return relative
