"""
CryticCompile main module. Handle the compilation.
"""
import base64
import glob
import inspect
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional, Set, Tuple, Type, Union

from crytic_compile.compilation_unit import CompilationUnit
from crytic_compile.platform import all_platforms, solc_standard_json
from crytic_compile.platform.abstract_platform import AbstractPlatform
from crytic_compile.platform.all_export import PLATFORMS_EXPORT
from crytic_compile.platform.solc import Solc
from crytic_compile.platform.standard import export_to_standard
from crytic_compile.utils.naming import Filename
from crytic_compile.utils.npm import get_package_name
from crytic_compile.utils.zip import load_from_zip

# Cycle dependency
if TYPE_CHECKING:
    pass

LOGGER = logging.getLogger("CryticCompile")
logging.basicConfig()


# pylint: disable=too-many-lines


def get_platforms() -> List[Type[AbstractPlatform]]:
    """
    Return the available platforms classes

    :return:
    """
    platforms = [getattr(all_platforms, name) for name in dir(all_platforms)]
    platforms = [d for d in platforms if inspect.isclass(d) and issubclass(d, AbstractPlatform)]
    return sorted(platforms, key=lambda platform: platform.TYPE)


def is_supported(target: str) -> bool:
    """
    Check if the target is supported

    :param target:
    :return:
    """
    platforms = get_platforms()
    return any(platform.is_supported(target) for platform in platforms) or target.endswith(".zip")


# pylint: disable=too-many-instance-attributes
class CryticCompile:
    """
    Main class.
    """

    def __init__(self, target: Union[str, AbstractPlatform], **kwargs: str):
        """
        Args:
            target (str|SolcStandardJson)
        Keyword Args:
            See https://github.com/crytic/crytic-compile/wiki/Configuration
        """

        # dependencies is needed for platform conversion
        self._dependencies: Set = set()

        # set containing all the filenames
        self._filenames: Set[Filename] = set()

        # mapping from absolute/relative/used to filename
        self._filenames_lookup: Optional[Dict[str, Filename]] = None

        self._src_content: Dict = {}

        # Mapping each file to
        #  offset -> line, column
        # This is not memory optimized, but allow an offset lookup in O(1)
        # Because we frequently do this lookup in Slither during the AST parsing
        # We decided to favor the running time versus memory
        self._cached_offset_to_line: Dict[Filename, Dict[int, Tuple[int, int]]] = dict()

        # Return the line from the line number
        # Note: line 1 is at index 0
        self._cached_line_to_code: Dict[Filename, List[bytes]] = dict()

        self._working_dir = Path.cwd()

        if isinstance(target, str):
            platform = self._init_platform(target, **kwargs)
        else:
            platform = target

        self._package = get_package_name(platform.target)

        self._platform: AbstractPlatform = platform

        self._compilation_units: Dict[str, CompilationUnit] = {}

        self._bytecode_only = False

        self._compile(**kwargs)

    @property
    def target(self) -> str:
        """
        Return the target (project)

        :return:
        """
        return self._platform.target

    @property
    def compilation_units(self) -> Dict[str, CompilationUnit]:
        """
        Return the dict id -> compilation unit

        """
        return self._compilation_units

    def is_in_multiple_compilation_unit(self, contract: str) -> bool:
        """
        Check if the contract is share by multiple compilation unit

        """
        count = 0
        for compilation_unit in self._compilation_units.values():
            if contract in compilation_unit.contracts_names:
                count += 1
        return count >= 2

    ###################################################################################
    ###################################################################################
    # region Filenames
    ###################################################################################
    ###################################################################################

    @property
    def filenames(self) -> Set[Filename]:
        """
        :return: set(naming.Filename)
        """
        return self._filenames

    @filenames.setter
    def filenames(self, all_filenames: Set[Filename]):
        self._filenames = all_filenames

    def filename_lookup(self, filename: str) -> Filename:
        """
        Return a crytic_compile.naming.Filename from a any filename form (used/absolute/relative)

        :param filename: str
        :return: crytic_compile.naming.Filename
        """
        if self._filenames_lookup is None:
            self._filenames_lookup = {}
            for file in self._filenames:
                self._filenames_lookup[file.absolute] = file
                self._filenames_lookup[file.relative] = file
                self._filenames_lookup[file.used] = file
        if filename not in self._filenames_lookup:
            raise ValueError(f"{filename} does not exist in {self._filenames_lookup}")
        return self._filenames_lookup[filename]

    @property
    def dependencies(self) -> Set[str]:
        """
        Return the dependencies files

        :return:
        """
        return self._dependencies

    def is_dependency(self, filename: str) -> bool:
        """
        Check if the filename is a dependency

        :param filename:
        :return:
        """
        return filename in self._dependencies or self.platform.is_dependency(filename)

    @property
    def package(self) -> Optional[str]:
        """
        Return the package name

        :return:
        """
        return self._package

    @property
    def working_dir(self) -> Path:
        """
        Return the working dir

        :return:
        """
        return self._working_dir

    @working_dir.setter
    def working_dir(self, path: Path):
        self._working_dir = path

    def _get_cached_offset_to_line(self, file: Filename):
        if file not in self._cached_line_to_code:
            self._get_cached_line_to_code(file)

        source_code = self._cached_line_to_code[file]
        acc = 0
        lines_delimiters: Dict[int, Tuple[int, int]] = dict()
        for line_number, x in enumerate(source_code):
            for i in range(acc, acc + len(x)):
                lines_delimiters[i] = (line_number + 1, i - acc + 1)
            acc += len(x)
        lines_delimiters[acc] = (len(source_code) + 1, 0)
        self._cached_offset_to_line[file] = lines_delimiters

    def get_line_from_offset(self, filename: str, offset: int) -> Tuple[int, int]:
        file = self.filename_lookup(filename)
        if file not in self._cached_offset_to_line:
            self._get_cached_offset_to_line(file)

        lines_delimiters = self._cached_offset_to_line[file]
        return lines_delimiters[offset]

    def _get_cached_line_to_code(self, file: Filename):
        source_code = self.src_content[file.absolute]
        source_code_encoded = source_code.encode("utf-8")
        source_code_list = source_code_encoded.splitlines(True)
        self._cached_line_to_code[file] = source_code_list

    def get_code_from_line(self, filename: str, line: int) -> Optional[bytes]:
        """
        Return the line from the file. Start at line = 1.
        Return None if the line is not in the file

        """
        file = self.filename_lookup(filename)
        if file not in self._cached_line_to_code:
            self._get_cached_line_to_code(file)

        lines = self._cached_line_to_code[file]
        if line - 1 < 0 or line - 1 >= len(lines):
            return None
        return lines[line - 1]

    @property
    def src_content(self) -> Dict[str, str]:
        """
        Return the source content, filename -> source_code

        :return:
        """
        # If we have no source code loaded yet, load it for every contract.
        if not self._src_content:
            for filename in self.filenames:
                if filename.absolute not in self._src_content and os.path.isfile(filename.absolute):
                    with open(filename.absolute, encoding="utf8", newline="") as source_file:
                        self._src_content[filename.absolute] = source_file.read()
        return self._src_content

    @src_content.setter
    def src_content(self, src):
        """
        Set the src_content

        :param src:
        :return:
        """
        self._src_content = src

    def src_content_for_file(self, filename_absolute: str) -> Union[str, None]:
        """
        Get the source code of the file

        :param filename_absolute:
        :return:
        """
        return self.src_content.get(filename_absolute, None)

    # endregion
    ###################################################################################
    ###################################################################################
    # region Type
    ###################################################################################
    ###################################################################################

    @property
    def type(self) -> int:
        """
        Return the type of the platform used

        :return:
        """
        # Type should have been set by now
        assert self._platform.TYPE
        return self._platform.TYPE

    @property
    def platform(self) -> AbstractPlatform:
        """
        Return the platform module

        :return:
        """
        assert self._platform
        return self._platform

    # endregion
    ###################################################################################
    ###################################################################################
    # region Compiler information
    ###################################################################################
    ###################################################################################

    @property
    def bytecode_only(self) -> bool:
        """
        Return true if only the bytecode was retrieved

        :return:
        """
        return self._bytecode_only

    @bytecode_only.setter
    def bytecode_only(self, bytecode):
        self._bytecode_only = bytecode

    # endregion
    ###################################################################################
    ###################################################################################
    # region Import
    ###################################################################################
    ###################################################################################

    @staticmethod
    def import_archive_compilations(compiled_archive: Union[str, Dict]) -> List["CryticCompile"]:
        """
        Import from an archive. compiled_archive is either a json file or the loaded dictionary
        The dictionary myst contain the "compilations" keyword

        :param compiled_archive:
        :return:
        """
        # If the argument is a string, it is likely a filepath, load the archive.
        if isinstance(compiled_archive, str):
            with open(compiled_archive, encoding="utf8") as file:
                compiled_archive = json.load(file)

        # Verify the compiled archive is of the correct form
        if not isinstance(compiled_archive, dict) or "compilations" not in compiled_archive:
            raise ValueError("Cannot import compiled archive, invalid format.")

        return [CryticCompile(archive) for archive in compiled_archive["compilations"]]

    # endregion

    ###################################################################################
    ###################################################################################
    # region Export
    ###################################################################################
    ###################################################################################

    def export(self, **kwargs: str) -> List[str]:
        """
        Export to json. The json format can be crytic-compile, solc or truffle.
        """
        export_format = kwargs.get("export_format", None)
        if export_format is None:
            return export_to_standard(self, **kwargs)
        if export_format not in PLATFORMS_EXPORT:
            raise Exception("Export format unknown")
        return PLATFORMS_EXPORT[export_format](self, **kwargs)

    # endregion
    ###################################################################################
    ###################################################################################
    # region Compile
    ###################################################################################
    ###################################################################################

    # pylint: disable=no-self-use
    def _init_platform(self, target: str, **kwargs: str) -> AbstractPlatform:
        platforms = get_platforms()
        platform = None

        compile_force_framework: Union[str, None] = kwargs.get("compile_force_framework", None)
        if compile_force_framework:
            platform = next(
                (p(target) for p in platforms if p.NAME.lower() == compile_force_framework.lower()),
                None,
            )

        if not platform:
            platform = next((p(target) for p in platforms if p.is_supported(target)), None)

        if not platform:
            platform = Solc(target)

        return platform

    def _compile(self, **kwargs: str):
        custom_build: Union[None, str] = kwargs.get("compile_custom_build", None)
        if custom_build:
            self._run_custom_build(custom_build)

        else:
            self._platform.compile(self, **kwargs)

        remove_metadata = kwargs.get("compile_remove_metadata", False)
        if remove_metadata:
            for compilation_unit in self._compilation_units.values():
                compilation_unit.remove_metadata()

    @staticmethod
    def _run_custom_build(custom_build: str):
        cmd = custom_build.split(" ")

        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            stdout_bytes, stderr_bytes = process.communicate()
            stdout, stderr = (
                stdout_bytes.decode(),
                stderr_bytes.decode(),
            )  # convert bytestrings to unicode strings

            LOGGER.info(stdout)
            if stderr:
                LOGGER.error("Custom build error: \n%s", stderr)

    # endregion
    ###################################################################################
    ###################################################################################
    # region NPM
    ###################################################################################
    ###################################################################################

    @property
    def package_name(self) -> Optional[str]:
        """
        :return: str or None
        """
        return self._package

    @package_name.setter
    def package_name(self, name: Optional[str]):
        self._package = name


# endregion
###################################################################################
###################################################################################


def compile_all(target: str, **kwargs: str) -> List[CryticCompile]:
    """
    Given a direct or glob pattern target, compiles all underlying sources and returns
    all the relevant instances of CryticCompile.

    :param target: A string representing a file/directory path or glob pattern denoting where compilation shouldoccur.
    :param kwargs: The remainder of the arguments passed through to all compilation steps.
    :return: Returns a list of CryticCompile instances for all compilations which occurred.
    """
    use_solc_standard_json = kwargs.get("solc_standard_json", False)

    # Attempt to perform glob expansion of target/filename
    globbed_targets = glob.glob(target, recursive=True)

    # Check if the target refers to a valid target already.
    # If it does not, we assume it's a glob pattern.
    compilations: List[CryticCompile] = []
    if os.path.isfile(target) or is_supported(target):
        if target.endswith(".zip"):
            compilations = load_from_zip(target)
        elif target.endswith(".zip.base64"):
            with tempfile.NamedTemporaryFile() as tmp:
                with open(target) as target_file:
                    tmp.write(base64.b64decode(target_file.read()))
                    compilations = load_from_zip(tmp.name)
        else:
            compilations.append(CryticCompile(target, **kwargs))
    elif os.path.isdir(target) or len(globbed_targets) > 0:
        # We create a new glob to find solidity files at this path (in case this is a directory)
        filenames = glob.glob(os.path.join(target, "*.sol"))
        if not filenames:
            filenames = glob.glob(os.path.join(target, "*.vy"))
            if not filenames:
                filenames = globbed_targets

        # Determine if we're using --standard-solc option to
        # aggregate many files into a single compilation.
        if use_solc_standard_json:
            # If we're using standard solc, then we generated our
            # input to create a single compilation with all files
            standard_json = solc_standard_json.SolcStandardJson()
            for filename in filenames:
                standard_json.add_source_file(filename)
            compilations.append(CryticCompile(standard_json, **kwargs))
        else:
            # We compile each file and add it to our compilations.
            for filename in filenames:
                compilations.append(CryticCompile(filename, **kwargs))
    else:
        raise ValueError(f"Unresolved target: {str(target)}")

    return compilations
