import bgraph.parsers
from bgraph.viewer.viewer import get_node_type


def test_get_node_type():
    # Test an empty node
    assert get_node_type({}) == "source"

    # If all type is set, return must be a list
    assert get_node_type({}, all_types=True) == ["source"]

    node_data = {"data": [{bgraph.parsers.SoongParser.SECTION_TYPE: "test"}]}

    assert get_node_type(node_data) == "test"

    node_data["data"].append(
        {
            bgraph.parsers.SoongParser.SECTION_TYPE: "other_test",
        }
    )

    # Only one of them is returned, but which is unknown
    assert get_node_type(node_data) in ("test", "other_test")

    # All of them are returned
    assert get_node_type(node_data, all_types=True) == ["test", "other_test"]
