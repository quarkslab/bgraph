import collections
import base64
import copy
import enum
import logging
import os
import pathlib
import xml.sax
import pyparsing  # type: ignore

# Improve performance by caching
pyparsing.ParserElement.enablePackrat()

import untangle  # type: ignore

import bgraph.exc
import bgraph.utils
from bgraph.types import (
    Any,
    cast,
    Dict,
    Final,
    List,
    Literal,
    Optional,
    overload,
    Section,
    TypedDict,
    Union,
)


logger: logging.Logger = bgraph.utils.create_logger(__name__)
"""Logger."""


class Manifest:
    """
    A Manifest (for AOSP) is an XML file listing all the projects used for a version of
    AOSP.

    The repository listing all the manifests is found at :
    https://android.googlesource.com/platform/manifest/

    This classes is a light wrapper around the XML File to query the parts of the
    manifest we are interested into.

    :param manifest_content: The content of a manifest
    """

    def __init__(self, manifest_content: str) -> None:
        """Constructor method"""
        try:
            self.xml: untangle.Element = untangle.parse(manifest_content)
        except xml.sax.SAXParseException as e:
            logger.exception(e)
            raise bgraph.exc.BGraphManifestException("Unable to load the manifest")

        if (
            getattr(self.xml, "manifest", False) is False
            or getattr(self.xml.manifest, "project", False) is False
        ):
            raise bgraph.exc.BGraphManifestException("Manifest misformed")

    def get_projects(self) -> Dict[str, str]:
        """Returns the list of the projects for a manifest.

        :return: A mapping between project name and project paths
        """
        project_map: Dict[str, str] = {}
        for project in self.xml.manifest.project:
            project_name = project["name"]
            project_path = project["path"]

            if project_name is not None and project_path is not None:
                project_map[project_name] = project_path
            else:
                logger.warning(
                    "Projet %s (@path: %s) is None", project_name, project_path
                )

        return project_map

    @classmethod
    def from_url(
        cls, manifest_name: str, other_url: Optional[str] = None
    ) -> "Manifest":
        """Loads a manifest from an URL

        Warning: This methods parses arbitrary data from an URL. Use with caution <!>

        If the other_url parameter is set, this will be used as an absolute URL.
        Otherwise, it will fetch data from the googlesource servers.

        :param manifest_name: Name of the manifest
        :param other_url: Use this url and not the one from Google
        :return: A `Manifest` class
        """
        try:
            import requests
        except ImportError:
            raise bgraph.exc.BGraphManifestException(
                "Must have requests installed for this action"
            )

        if other_url is None:
            url_content = f"https://android.googlesource.com/platform/manifest/+/refs/heads/{manifest_name}/default.xml?format=TEXT"
        else:
            url_content = other_url

        try:
            response = requests.get(url_content)
        except requests.exceptions.RequestException as e:
            raise bgraph.exc.BGraphManifestException(e)

        try:
            xml_string: str = base64.decodebytes(response.content).decode(
                response.encoding
            )
        except TypeError as e:
            raise bgraph.exc.BGraphManifestException(e)

        return cls(manifest_content=xml_string)

    @classmethod
    def from_file(cls, file_path: Union[str, pathlib.Path]) -> "Manifest":
        """Load a Manifest from a file

        :param file_path: A PathLike object pointing to a file.
        :return: A `Manifest` class.
        """
        file_path = pathlib.Path(file_path)

        if file_path.is_file():
            return cls(manifest_content=file_path.as_posix())

        raise bgraph.exc.BGraphManifestException()


class SoongParser:
    """Soong Parser

    This is the wrapper around the parser for Soong file (e.g. Android.bp)

    Every section will be augmented with special keys (always prefixed with soong_parser).

    """

    SECTION_TYPE: Final = "soong_parser_section_type"
    """Type of the section (e.g. cc_library)."""

    SECTION_PROJECT: Final = "soong_parser_section_project"
    """Name of the project for the current section."""

    SECTION_PROJECT_PATH: Final = "soong_parser_project_path"
    """Absolute path of the project in AOSP root tree."""

    SOONG_FILE: Final = "soong_parser_soong_path"
    """Absolute path of the Soong file in AOSP root tree."""

    DEFAULT_FILENAME: Final = "Android.bp"
    """Default name for Soong file."""

    NATIVE_TYPES: List[str] = [
        "cc_binary",
        "cc_library",
        "cc_library_shared",
        "cc_library_static",
    ]
    """Type of section considered as "natives"."""

    def __init__(self) -> None:
        """Init method."""
        self.sections: Dict[str, List[Section]] = collections.defaultdict(list)
        self.variables: Dict[str, Any] = {}

        self._files_listing: Dict[pathlib.Path, List[str]] = {}

    # Public API
    def list_section(self, with_defaults: bool = False) -> List[str]:
        """List sections found in AOSP.

        :param with_defaults: Also include defaults sections in the results
        :return: A list of sections
        """
        section_list: List[str] = []
        for section_name, targets in self.sections.items():
            if with_defaults or any(
                "default" not in target.get(self.SECTION_TYPE, "") for target in targets
            ):
                section_list.append(section_name)

        return section_list

    @overload
    def get_section(self, section_name: str) -> List[Section]:
        ...

    @overload
    def get_section(self, section_name: str, section_type: str) -> Section:
        ...

    def get_section(
        self, section_name: str, section_type: Optional[str] = None
    ) -> Union[List[Section], Section]:
        """Get a section from the project.

        This is the main method of the class. It will also resolve the section defaults if
        any are found. Note that the name *must* be exact.

        :param section_name: Name of the section
        :param section_type: Optional. Type of the section. If the type is defined, a
            single section will be returned of matching type. Otherwise all sections
            having the same name will be returned.
        :return: A (list of) sections having the name asked.
        """

        sections: List[Section] = self._retrieve_section(section_name)
        if section_type is None:
            return sections

        for section in sections:
            if section[self.SECTION_TYPE] == section_type:
                return section

        raise bgraph.exc.BGraphMissingSectionException()

    def parse_file(
        self,
        file_path: Union[str, pathlib.Path],
        project_name: str = None,
        project_path: Optional[pathlib.Path] = None,
        project_variables: Dict[str, Any] = None,
    ) -> None:
        """Parse a file (e.g. an Android.bp) and update the current class.

        Note: This will silently fails if the file is misformed.

        :param file_path: Path towards the file
        :param project_name: Optional. Name of the current project
        :param project_path: Optional. Path to the root of the project
        :param project_variables: Variables already set for the project
        """
        if project_variables is None:
            project_variables = {}

        try:
            parser = SoongFileParser(file_path, project_variables)
        except bgraph.exc.BGraphParserException:
            # The parser is a best effort one. If it fails, do not try to hard but
            # report the error if in DEBUG mode.
            logger.debug("Failed to parse %s", file_path)
            return

        # If we are doing a parsing of a project, we want to store more information on
        # the sections, namely where was the initial file located and the root source of
        # the project. This will be handy when resolving relative paths.
        if project_name is not None:
            for section_name, sections in parser.sections.items():
                for section in sections:
                    section[self.SECTION_PROJECT] = project_name
                    section[self.SOONG_FILE] = pathlib.Path(file_path)

                    if project_path is not None:
                        section[self.SECTION_PROJECT_PATH] = project_path

                    self.sections[section_name].append(section)

        project_variables.update(parser.variables)
        self.variables.update(parser.variables)

    def parse_aosp(
        self,
        aosp_directory: Union[str, pathlib.Path],
        file_name: Optional[str] = None,
        project_map: Dict = None,
    ) -> None:
        """Parses an AOSP tree.

        This methods only needs the soong file to be present so a partial checkout is
        enough to create the listing.

        The project map is needed because it needs to know the root tree of a project.

        :param aosp_directory: Root tree of AOSP
        :param file_name: Optional Name of file
        :param project_map: A map of project name / project path
        """
        if file_name is None:
            file_name = self.DEFAULT_FILENAME

        if project_map is None:
            raise bgraph.exc.BGraphParserException("Missing project map.")

        aosp_directory = pathlib.Path(aosp_directory)
        for project_name, relative_path in project_map.items():
            project_path = aosp_directory / relative_path
            self.parse_project(
                project_directory=project_path,
                file_name=file_name,
                project_name=project_name,
            )

    def parse_project(
        self,
        project_directory: Union[str, pathlib.Path],
        project_name: str,
        file_name: Optional[str] = None,
    ) -> None:
        """Parse a project inside AOSP

        This methods expects the project to be an AOSP project (e.g. an entry in the
        manifest list of projects).

        :param project_directory: Path towards the project
        :param project_name: Name of the project
        :param file_name: Name of the soong files
        """
        if file_name is None:
            file_name = self.DEFAULT_FILENAME

        project_directory = pathlib.Path(project_directory)
        project_variables: Dict[str, Any] = {}
        for soong_file in project_directory.rglob(file_name):
            self.parse_file(
                file_path=soong_file,
                project_name=project_name,
                project_path=project_directory,
                project_variables=project_variables,
            )

        # Sometimes in Android, a project may be have additional "generic" components
        # We try to include also Build Files files from those directories here to handle this case
        # This is a *dirty* hack and it should not be necessary when the project is from
        # the manifest.
        for soong_file in (project_directory.parent / "generic").rglob(file_name):
            self.parse_file(file_path=soong_file)

    def get_targets(self) -> List[str]:
        """Compute the list of targets.

        A section is considered to be a target if the section_type is a binary type.
        This method is for now pretty simplist but could be improved.

        TODO:
            - add target parameter to filter targets
            - Filter also according to the value for the arch
            - add multi arch support
            - host/target difference

        :return: A list of section having a "binary" target.
        """
        target_list: List[str] = []
        for section_name in self.list_section(with_defaults=False):
            section_map: List[Section] = self.get_section(section_name)

            for section in section_map:
                section_type = section.get(self.SECTION_TYPE)

                if section_type in [
                    "cc_library",
                    "cc_library_shared",
                    "cc_library_static",
                ]:
                    # The target is actually the name of the section. Manual says it can
                    # be overriden but I did not find any evidence of that.
                    # TODO(dm) : see if the name if overriden & check if the lib is not
                    #  disabled for target ? (how?)
                    target_list.append(section_name)
                elif section_type in [
                    "cc_binary",
                ]:
                    target_list.append(section_name)

        return target_list

    @property
    def file_listing(self) -> Dict[pathlib.Path, List[str]]:
        """A map of every paths and files inside the project.
        This is used to resolve wildcards in filenames for Soong.

        :return: A maping between path and list of files inside an AOSP tree.
        """
        return self._files_listing

    @file_listing.setter
    def file_listing(self, listing: Dict[pathlib.Path, List[str]]) -> None:
        """Setter for the property

        :param listing: File listing (mapping between Paths and list of files)
        """
        self._files_listing = listing

    # Private method
    # ##############
    @overload
    def _retrieve_section(self, section_name: str, recursive: bool) -> Section:
        ...

    @overload
    def _retrieve_section(self, section_name: str) -> List[Section]:
        ...

    def _retrieve_section(
        self, section_name: str, recursive: bool = False
    ) -> Union[List[Section], Section]:
        """Retrieve a section in the project.

        If recursive is Fasle:
            This will iterate recursively until every defaults is resolved and the list of
            sections returned.
        If recursive is True:
            Yields only one section (the defaults)

        :param section_name: Name of the section
        :param recursive: Already a recursive call?
        :return: A section or a list of sections
        """
        # Check if section name exists
        projects = self.sections.get(section_name)
        if projects is None:
            raise bgraph.exc.BGraphMissingSectionException()

        # Iterate through the sections
        for index, section_map in enumerate(projects):
            defaults_list = section_map.get("defaults")
            if defaults_list is None:
                continue

            if type(defaults_list) is not list:
                defaults_list = [cast(str, defaults_list)]

            for default_name in defaults_list:

                try:
                    # TODO(dm) support for multiple defined defaults
                    default_map: Section = self._retrieve_section(
                        default_name, recursive=True
                    )
                    section_map = self._merge_section(section_map, default_map)
                except bgraph.exc.BGraphMissingSectionException:
                    # Sometimes the defaults section are not defined inside the project
                    # Instead of parsing the whole AOSP Tree (the good thing to do) we
                    # just ignore this kind of errors
                    continue

            self.sections[section_name][index] = section_map
            del self.sections[section_name][index]["defaults"]

        if recursive is True:
            return self.sections[section_name][0]
        else:
            return self.sections[section_name]

    @staticmethod
    def _merge_section(section_map: Section, default_map: Section) -> Section:
        """Merge a section with its default.

        Its uses every value of the default and overrides them if they are redefined in
        the parent one.

        List and Dicts are merged and other values overriden.

        :param section_map: Intial map
        :param default_map: Default map
        :return: An updated initial map.
        """

        def recursive_merge(mapping, local_key, local_val):
            if local_key not in mapping:
                mapping[local_key] = local_val
            else:
                # Overwrite the value in case of boolean or string
                if type(local_val) in (str, bool, int):
                    mapping[local_key] = local_val

                elif type(local_val) is list:
                    mapping[local_key] = local_val + list(mapping[local_key])

                elif type(local_val) is dict:
                    for nested_key, nested_val in local_val.items():
                        recursive_merge(mapping[local_key], nested_key, nested_val)

                else:  # For other types (like Paths), overwrite
                    mapping[local_key] = local_val

        final_map = copy.deepcopy(default_map)
        for key, val in section_map.items():
            recursive_merge(final_map, key, val)

        return final_map


class SoongFileParser:
    """Parser for soong files

    Set and parse a soong file.
    This is a best effort parser and some edge cases are not supported.

    :arg file_path (str, Path): A path towards the blueprint file to parse
    :arg variables A mapping of variable already set

    :raise BGraphParserException When an error occurs during the parsing

    :param variables (Dict): Mapping of variables and their value inside the Blueprint file
    :param sections (Dict): Mapping of the sections and their content
    """

    def __init__(
        self,
        file_path: Optional[Union[pathlib.Path, str]] = None,
        variables: Dict[str, Any] = None,
    ):
        """Constructor"""
        self.variables: Dict[str, Any] = {}
        if variables is not None:
            self.variables = variables

        self.identifiers: Dict[str, Any] = {}

        self.sections: Dict[str, List[Section]] = collections.defaultdict(list)

        self.parser: pyparsing.ParserElement = self._init_parser()

        if file_path:
            self.parser.parseFile(pathlib.Path(file_path).as_posix())
            if self.identifiers or not (self.sections or self.variables):

                raise bgraph.exc.BGraphParserException("An error ocured during parsing")

    # Parsing method helpers
    @staticmethod
    def parse_boolean(tokens: List[Any]) -> bool:
        """Helper method to parse boolean

        :param tokens: List of tokens
        :raises BGraphParserException: When the boolean is not true or false
        :return: A boolean
        """
        token = tokens[0]
        if token == "true":
            return True
        elif token == "false":
            return False

        raise bgraph.exc.BGraphParserException("Boolean exception")

    @staticmethod
    def parse_integer(tokens: List[str]) -> int:
        """Helper method to parse integers

        :param tokens: Tokens
        :return: An integer
        """
        return int(tokens[0])

    def parse_variable_ref(self, tokens: List[str]) -> Any:
        """Helper method to parse variable reference

        :param tokens: Tokens to parse
        :raises: BGraphParserException When the variables is used before being defined

        :return: The variable value

        """
        var_name: str = tokens[0]
        if var_name not in self.variables:
            raise bgraph.exc.BGraphParserException("Missing variable ref var_name")

        return self.variables[var_name]

    def parse_variable_def(
        self, _, __, tokens: List[Any], append: bool = False
    ) -> None:
        """Helper method to parse variable definition

        :param _: N/A
        :param __: N/A
        :param tokens: Tokens to parse
        :param append: Should we appended the value to the existing one or not
        :raises BGraphParserException: When the parsing fails
        """
        variable_name = tokens[0]
        new_value = tokens[1] if len(tokens) == 2 else tokens[1:]
        if append is False:
            old_value = self.variables.get(variable_name, None)
            if old_value is not None and old_value != new_value:
                logger.debug("Overwritting variable - in debug, check if legit.")
                # raise bgraph.exc.BGraphParserException("Conflicting variables names")

            self.variables[variable_name] = new_value

        else:
            actual_value = self.variables.get(variable_name)
            if actual_value is None:
                raise bgraph.exc.BGraphParserException(
                    "Missing previous variable during append"
                )

            if type(new_value) != type(actual_value):
                new_value = [new_value] if type(new_value) is str else new_value
                actual_value = (
                    [actual_value] if type(actual_value) is str else actual_value
                )

            self.variables[variable_name] = actual_value + new_value

    @staticmethod
    def parse_string_concat(tokens: List[str]) -> Optional[str]:
        """Helper method to concat string together

        :param tokens: Tokens
        :return: Optionnaly a string string
        """
        final_token = ""
        for token in tokens:
            if type(token) is str:
                final_token += token
            else:
                # Do not raise an exception as it may mess up with pyparsing
                return None

        return final_token

    @staticmethod
    def parse_list_concat(tokens: List[str]) -> List[Any]:
        """Helper for list concatenation

        :param tokens: Tokens
        :return: A list of tokens
        """

        final_list: List[Any] = []
        for token in tokens:
            if type(token) is list:
                final_list.extend(token)
            elif type(token) is str:
                final_list.append(token)
            else:
                # Do not raise an exception as it may mess with pyparsing
                return []

        return final_list

    @staticmethod
    def parse_dict_field(tokens) -> Dict:
        """Helper method to parse a map"""
        key = tokens[0]
        val = tokens[1] if len(tokens) == 2 else tokens[1:]

        return {key: val}

    @staticmethod
    def parse_dict_def(tokens) -> Dict:
        """Helper method to parse the dict definition"""
        result_dict = {}
        for token in tokens:
            result_dict.update(token)

        return result_dict

    def parse_section_field(self, tokens: List[str]) -> str:
        """Parse a section field

        Example:
            name: "libartbase_defaults"

        :return The name of the field
        """

        if len(tokens) == 2:
            self.identifiers[tokens[0]] = tokens[1]
        elif len(tokens) > 2:
            self.identifiers[tokens[0]] = tokens[1:]
        elif len(tokens) == 1:
            # FIX: handle empty definitions like whole_static_libs: []
            self.identifiers[tokens[0]] = []

        return tokens[0]

    def parse_section(self, tokens: List[str]) -> None:
        """Parse a section

        :param tokens: Tokens
        :raises BGraphParserException: If the parsing of the section fails
        """
        section_name = None
        section_dict: Section = {SoongParser.SECTION_TYPE: tokens[0]}
        for token in tokens[1:]:
            if token in self.identifiers:

                if token == "name":
                    section_name = self.identifiers[token]
                else:
                    # TODO(dm) This will be resolved when we have a way to type hint a
                    #   dict with dynamic values
                    section_dict[token] = self.identifiers[token]  # type: ignore

                del self.identifiers[token]
            else:
                raise bgraph.exc.BGraphParserException(
                    "Missing key {} in section {}".format(token, section_name)
                )

        # Each section *must* have a name
        if section_name is None:
            # Except soong_namespace ...
            if section_dict[SoongParser.SECTION_TYPE] in ("soong_namespace",):
                logger.debug("Found a soong namespace but it is not supported yet.")
                return

            raise bgraph.exc.BGraphParserException("Section has no attribute name")

        self.sections[section_name].append(section_dict)

    def _init_parser(self) -> pyparsing.ParserElement:
        """Main method: create the parser for the blueprint syntax.

        This is a best effort parser and some edges cases are not correct. A lof of work
        would be needed here to improve this, maybe by trying to find an automated parser
        generation tool?

        TODO(dm):
            - Map append {} + {}

        :return: A pyparsing Parser
        """

        # Basic types
        lparen, rparen, lbrack, rbrack, lbrace, rbrace, colon, comma, equal, plus = map(
            pyparsing.Suppress, "()[]{}:,=+"
        )
        quoted_string = pyparsing.QuotedString(
            quoteChar='"', escChar="\\", multiline=True, unquoteResults=True
        ).setName("quoted-string")

        # Boolean
        true = pyparsing.Keyword("true")
        false = pyparsing.Keyword("false")
        boolean = true | false
        boolean.setName("bool").setParseAction(self.parse_boolean)

        # Identifiers & variables references
        # FIX: does not allow variable starting with numbers
        variable = ~boolean + pyparsing.Word(
            pyparsing.alphas + "_", pyparsing.alphanums + "_"
        )
        identifier = variable.copy().setName("identifier")
        variable_ref = (
            variable.copy().setName("var-ref").setParseAction(self.parse_variable_ref)
        )

        # Integers (not used?)
        integer = (
            pyparsing.Word(pyparsing.nums)
            .setName("integer")
            .setParseAction(self.parse_integer)
        )

        # String concatenation
        string_concat = pyparsing.delimitedList(
            quoted_string | variable_ref, delim=plus
        )
        string_concat.setName("string-concat").setParseAction(self.parse_string_concat)

        # List of strings
        string_list = (
            lbrack
            + pyparsing.ZeroOrMore(pyparsing.delimitedList(string_concat, delim=comma))
            + pyparsing.Optional(comma)
            + rbrack
        )

        string_list.setParseAction(lambda t: [t[::]]).setName("string-list")

        # List concatenation: ref + list // list + list // var + var
        list_concat = pyparsing.delimitedList(variable_ref | string_list, delim=plus)
        list_concat.setName("list-concat").setParseAction(self.parse_list_concat)

        # Dict special field
        dict_body = pyparsing.Forward()
        dict_def = lbrace + dict_body("dict_body") + pyparsing.Optional(comma) + rbrace
        dict_def.setName("dict-def")

        # All possibles values for a "value" (order does not matter)
        value = pyparsing.Or(
            [
                boolean,
                integer,
                quoted_string,
                variable_ref,
                string_list,
                dict_def,
                list_concat,
                string_concat,
            ]
        )

        # Continue dict definition
        dict_field = identifier + colon + value
        dict_field.setParseAction(self.parse_dict_field)
        dict_body <<= pyparsing.ZeroOrMore(pyparsing.delimitedList(dict_field))
        dict_def.setParseAction(self.parse_dict_def)

        # Sections definitions
        section_body = pyparsing.Forward()

        section_def = (
            identifier + lbrace + section_body + pyparsing.Optional(comma) + rbrace
        )
        section_field = identifier + colon + value
        section_field.setParseAction(self.parse_section_field)
        section_body <<= pyparsing.ZeroOrMore(pyparsing.delimitedList(section_field))

        section_def.setName("section-def").setParseAction(self.parse_section)

        # We can also have direct variables
        variable_def = (
            identifier.setResultsName("var-name")
            + equal
            + value.setResultsName("var-value")
        )
        # variable_def = identifier + equal + value
        variable_def.setName("var-def").setParseAction(self.parse_variable_def)

        variable_append = identifier + pyparsing.Literal("+=").suppress() + value
        variable_append.setName("var-append").setParseAction(
            lambda s, l, t: self.parse_variable_def(s, l, t, append=True)
        )

        parser = pyparsing.ZeroOrMore(section_def | variable_def | variable_append)
        parser.ignore(pyparsing.cppStyleComment | pyparsing.cStyleComment)

        return parser
