from bgraph.parsers.soong_parser import SoongFileParser, SoongParser
from pathlib import Path


TEST_DIR = Path(__file__).parent.parent


def get_blueprint_path(file_path: str) -> Path:
    path = TEST_DIR / "data" / "blueprints" / f"{file_path}.bp"
    return path


def get_first_section(soong_parser: SoongFileParser, section_name: str):
    sections = soong_parser.sections.get(section_name, {})
    if sections:
        return sections[0]

    raise IndexError("Section not found")


def test_simple_module():
    soong_parser = SoongFileParser(get_blueprint_path("module"))

    assert "linker" in soong_parser.sections
    assert len(soong_parser.sections["linker"]) == 1

    linker = soong_parser.sections["linker"].pop()

    assert linker[SoongParser.SECTION_TYPE] == "cc_binary"


def test_boolean_parsing():
    soong_parser = SoongFileParser(get_blueprint_path("boolean"))
    section = get_first_section(soong_parser, "linker")

    assert section["static_executable"] is True
    assert section["native_coverage"] is False


def test_list_parsing():
    soong_parser = SoongFileParser(get_blueprint_path("lists"))
    section = get_first_section(soong_parser, "linker")

    assert len(section["cflags"]) == 3
    diff = set(section["cflags"]) ^ {
        "-DHAVE_CONFIG_H",
        "-DSIZEOF_KERNEL_LONG_T=SIZEOF_LONG",
        "-DSIZEOF_OFF_T=SIZEOF_LONG",
    }
    assert not diff


def test_variables_parsing():
    soong_parser = SoongFileParser(get_blueprint_path("variables"))
    section = get_first_section(soong_parser, "linker")

    assert section["value_int"] == 2
    # TODO(dm) THIS TEST FAILS
    # assert section["subdirs"] == ["*"]

    assert "value" in soong_parser.variables
    assert "subdirs" in soong_parser.variables


def test_dict_parsing():
    soong_parser = SoongFileParser(get_blueprint_path("dict"))
    section = get_first_section(soong_parser, "libnfc-nci")

    assert section.get("arch") is not None
    assert section["arch"].get("arm", {}).get("instruction_set") == "arm"
