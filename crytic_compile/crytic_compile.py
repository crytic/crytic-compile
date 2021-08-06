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
from collections import defaultdict
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
    """Return the available platforms classes

    Returns:
        List[Type[AbstractPlatform]]: Available platforms
    """
    platforms = [getattr(all_platforms, name) for name in dir(all_platforms)]
    platforms = [d for d in platforms if inspect.isclass(d) and issubclass(d, AbstractPlatform)]
    return sorted(platforms, key=lambda platform: platform.TYPE)


def is_supported(target: str) -> bool:
    """Check if the target is supporte. Iterate over all known platforms

    Args:
        target (str): path to the target

    Returns:
        bool: True if the target is supported
    """
    platforms = get_platforms()
    return any(platform.is_supported(target) for platform in platforms) or target.endswith(".zip")


# pylint: disable=too-many-instance-attributes
class CryticCompile:
    """
    Main class.
    """

    def __init__(self, target: Union[str, AbstractPlatform], **kwargs: str):
        """See https://github.com/crytic/crytic-compile/wiki/Configuration
        Target is usually a file or a project directory. It can be an AbstractPlatform
        for custom setup

        Args:
            target (Union[str, AbstractPlatform]): Target
            **kwargs: additional arguments
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
        # Lines are indexed from 1
        self._cached_line_to_offset: Dict[Filename, Dict[int, int]] = defaultdict(dict)

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
        """Return the project's target

        Returns:
            str: target
        """
        return self._platform.target

    @property
    def compilation_units(self) -> Dict[str, CompilationUnit]:
        """Return the compilation units

        Returns:
            Dict[str, CompilationUnit]: compilation id => CompilationUnit
        """
        return self._compilation_units

    def is_in_multiple_compilation_unit(self, contract: str) -> bool:
        """Check if the contract is shared by multiple compilation unit

        Args:
            contract (str): contract name

        Returns:
            bool: True if the contract is in multiple compilation units
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
        """All the project filenames

        Returns:
            Set[Filename]: Project's filenames
        """
        return self._filenames

    @filenames.setter
    def filenames(self, all_filenames: Set[Filename]) -> None:
        """Set the filenames

        Args:
            all_filenames (Set[Filename]): New filenames
        """
        self._filenames = all_filenames

    def filename_lookup(self, filename: str) -> Filename:
        """Return a crytic_compile.naming.Filename from a any filename

        Args:
            filename (str): filename (used/absolute/relative)

        Raises:
            ValueError: If the filename is not in the project

        Returns:
            Filename: Associated Filename object
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
        """Return the dependencies files

        Returns:
            Set[str]: Dependencies files
        """
        return self._dependencies

    def is_dependency(self, filename: str) -> bool:
        """Check if the filename is a dependency

        Args:
            filename (str): filename

        Returns:
            bool: True if the filename is a dependency
        """
        return filename in self._dependencies or self.platform.is_dependency(filename)

    @property
    def package(self) -> Optional[str]:
        """Return the package name

        Returns:
            Optional[str]: package name
        """
        return self._package

    @property
    def working_dir(self) -> Path:
        """Return the working directory

        Returns:
            Path: Working directory
        """
        return self._working_dir

    @working_dir.setter
    def working_dir(self, path: Path) -> None:
        """Set the working directory

        Args:
            path (Path): new working directory
        """
        self._working_dir = path

    def _get_cached_offset_to_line(self, file: Filename) -> None:
        """Compute the cached offsets to lines

        Args:
            file (Filename): filename
        """
        if file not in self._cached_line_to_code:
            self._get_cached_line_to_code(file)

        source_code = self._cached_line_to_code[file]
        acc = 0
        lines_delimiters: Dict[int, Tuple[int, int]] = dict()
        for line_number, x in enumerate(source_code):
            self._cached_line_to_offset[file][line_number + 1] = acc

            for i in range(acc, acc + len(x)):
                lines_delimiters[i] = (line_number + 1, i - acc + 1)

            acc += len(x)
        lines_delimiters[acc] = (len(source_code) + 1, 0)
        self._cached_offset_to_line[file] = lines_delimiters

    def get_line_from_offset(self, filename: Union[Filename, str], offset: int) -> Tuple[int, int]:
        """Return the line from a given offset

        Args:
            filename (Union[Filename, str]): filename
            offset (int): global offset

        Returns:
            Tuple[int, int]: (line, line offset)
        """
        if isinstance(filename, str):
            file = self.filename_lookup(filename)
        else:
            file = filename
        if file not in self._cached_offset_to_line:
            self._get_cached_offset_to_line(file)

        lines_delimiters = self._cached_offset_to_line[file]
        return lines_delimiters[offset]

    def get_global_offset_from_line(self, filename: Union[Filename, str], line: int) -> int:
        """Return the global offset from a given line

        Args:
            filename (Union[Filename, str]): filename
            line (int): line

        Returns:
            int: global offset
        """
        if isinstance(filename, str):
            file = self.filename_lookup(filename)
        else:
            file = filename
        if file not in self._cached_line_to_offset:
            self._get_cached_offset_to_line(file)

        return self._cached_line_to_offset[file][line]

    def _get_cached_line_to_code(self, file: Filename) -> None:
        """Compute the cached lines

        Args:
            file (Filename): filename
        """
        source_code = self.src_content[file.absolute]
        source_code_encoded = source_code.encode("utf-8")
        source_code_list = source_code_encoded.splitlines(True)
        self._cached_line_to_code[file] = source_code_list

    def get_code_from_line(self, filename: Union[Filename, str], line: int) -> Optional[bytes]:
        """Return the code from the line. Start at line = 1.
        Return None if the line is not in the file

        Args:
            filename (Union[Filename, str]): filename
            line (int): line

        Returns:
            Optional[bytes]: line of code
        """
        if isinstance(filename, str):
            file = self.filename_lookup(filename)
        else:
            file = filename
        if file not in self._cached_line_to_code:
            self._get_cached_line_to_code(file)

        lines = self._cached_line_to_code[file]
        if line - 1 < 0 or line - 1 >= len(lines):
            return None
        return lines[line - 1]

    @property
    def src_content(self) -> Dict[str, str]:
        """Return the source content

        Returns:
            Dict[str, str]: filename -> source_code
        """
        # If we have no source code loaded yet, load it for every contract.
        if not self._src_content:
            for filename in self.filenames:
                if filename.absolute not in self._src_content and os.path.isfile(filename.absolute):
                    with open(filename.absolute, encoding="utf8", newline="") as source_file:
                        self._src_content[filename.absolute] = source_file.read()
        return self._src_content

    @src_content.setter
    def src_content(self, src: Dict) -> None:
        """Set the source content

        Args:
            src (Dict): New source content
        """
        self._src_content = src

    def src_content_for_file(self, filename_absolute: str) -> Optional[str]:
        """Get the source code of the file

        Args:
            filename_absolute (str): absolute filename

        Returns:
            Optional[str]: source code
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
        """Return the type of the platform used

        Returns:
            int: Platform type (see AbstractPatform.TYPE)
        """
        # Type should have been set by now
        assert self._platform.TYPE
        return self._platform.TYPE

    @property
    def platform(self) -> AbstractPlatform:
        """Return the underlying platform

        Returns:
            AbstractPlatform: Underlying platform
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
        """Return true if only the bytecode was retrieved.
        This can only happen for the etherscan platform

        Returns:
            bool: True if the project is bytecode only
        """
        return self._bytecode_only

    @bytecode_only.setter
    def bytecode_only(self, bytecode: bool) -> None:
        """Set the bytecode_only info (only for etherscan)

        Args:
            bytecode (bool): new bytecode_only status
        """
        self._bytecode_only = bytecode

    # endregion
    ###################################################################################
    ###################################################################################
    # region Import
    ###################################################################################
    ###################################################################################

    # TODO: refactor import_archive_compilations to rely on one CryticCompile object
    # But multiple compilation units
    @staticmethod
    def import_archive_compilations(compiled_archive: Union[str, Dict]) -> List["CryticCompile"]:
        """Import from an archive. compiled_archive is either a json file or the loaded dictionary
        The dictionary myst contain the "compilations" keyword

        Args:
            compiled_archive: Union[str, Dict]: list of archive to import

        Raises:
            ValueError: The import did not worked

        Returns:
            [CryticCompile]: List of crytic compile object
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
        """Export to json.
        The json format can be crytic-compile, solc or truffle.
        The type must be specified in the kwargs with "export_format"

        Args:
            **kwargs: optional arguments. Used: "export_format"

        Raises:
            ValueError: Incorrect type

        Returns:
            List[str]: List of the filenames generated
        """
        export_format = kwargs.get("export_format", None)
        if export_format is None:
            return export_to_standard(self, **kwargs)
        if export_format not in PLATFORMS_EXPORT:
            raise ValueError("Export format unknown")
        return PLATFORMS_EXPORT[export_format](self, **kwargs)

    # endregion
    ###################################################################################
    ###################################################################################
    # region Compile
    ###################################################################################
    ###################################################################################

    # pylint: disable=no-self-use
    def _init_platform(self, target: str, **kwargs: str) -> AbstractPlatform:
        """Init the platform

        Args:
            target (str): path to the target
            **kwargs: optional arguments. Used: "compile_force_framework", "compile_custom_build", "compile_remove_metadata"


        Returns:
            AbstractPlatform: Underlying platform
        """
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

    def _compile(self, **kwargs: str) -> None:
        """Compile the project

        Args:
            **kwargs: optional arguments. Used: "compile_custom_build", "compile_remove_metadata"
        """
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
    def _run_custom_build(custom_build: str) -> None:
        """Run a custom build

        Args:
            custom_build (str): Command to run
        """
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
        """Return the npm package name

        Returns:
            Optional[str]: Package name
        """
        return self._package

    @package_name.setter
    def package_name(self, name: Optional[str]) -> None:
        """Set the package name

        Args:
            name (Optional[str]): New package name
        """
        self._package = name


# endregion
###################################################################################
###################################################################################

# TODO: refactor me to be integarted within CryticCompile.__init__
def compile_all(target: str, **kwargs: str) -> List[CryticCompile]:
    """Given a direct or glob pattern target, compiles all underlying sources and returns
    all the relevant instances of CryticCompile.

    Args:
        target (str): A string representing a file/directory path or glob pattern denoting where compilation should occur.
        **kwargs: optional arguments. Used: "solc_standard_json"

    Raises:
        ValueError: If the target could not be compiled

    Returns:
        List[CryticCompile]: Returns a list of CryticCompile instances for all compilations which occurred.
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
