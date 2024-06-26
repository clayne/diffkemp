"""Unit tests for the Callstack and YamlOutput class."""
from diffkemp.output import YamlOutput
from diffkemp.semdiff.caching import ComparisonGraph, _get_callstack
from diffkemp.semdiff.result import Result
from diffkemp.utils import get_end_line
import pytest


def test_callstack_from_edge_objects(graph):
    """Tests creation of Callstack from callstack consisting of Edge objects.
    """
    _, map = graph.reachable_from(ComparisonGraph.Side.LEFT, "main_function")
    edges = _get_callstack(map, graph["main_function"], graph["do_check"])
    callstack = Result.Callstack.from_edge_objects(edges)
    assert callstack.calls == [
        {"name": "do_check", "file": "app/main.c", "line": 58}
    ]


def test_callstack_from_simpll_yaml(graph):
    """Tests creation of Callstack from representation used in non-fun diffs.
    """
    macro = [nonfun_diff for nonfun_diff in graph["do_check"].nonfun_diffs
             if nonfun_diff.name == "___MACRO"][0]
    callstack = Result.Callstack.from_simpll_yaml(
        macro.callstack[ComparisonGraph.Side.LEFT])
    assert callstack.calls == [
        {"name": "_MACRO (macro)", "file": "test.c", "line": 1},
        {"name": "__MACRO (macro)", "file": "test.c", "line": 2},
        {"name": "___MACRO (macro)", "file": "test.c", "line": 3}
    ]


def test_callstack_add():
    """Tests addition of Callstacks."""
    parent_calls = Result.Callstack([
        {"name": "do_check", "file": "app/main.c", "line": 58}
    ])
    calls = Result.Callstack([
        {"name": "_MACRO (macro)", "file": "test.c", "line": 1},
        {"name": "__MACRO (macro)", "file": "test.c", "line": 2},
        {"name": "___MACRO (macro)", "file": "test.c", "line": 3}
    ])
    all_calls = parent_calls + calls
    assert all_calls.calls == ([
        {"name": "do_check", "file": "app/main.c", "line": 58},
        {"name": "_MACRO (macro)", "file": "test.c", "line": 1},
        {"name": "__MACRO (macro)", "file": "test.c", "line": 2},
        {"name": "___MACRO (macro)", "file": "test.c", "line": 3}
    ])


@pytest.fixture
def callstack():
    yield Result.Callstack([
        {"name": "name1", "file": "/home/user/linux/file1", "line": 1},
        {"name": "name2 (macro)", "file": "/home/user/linux/src/file2",
         "line": 2}
    ])


def test_callstack_str(callstack):
    """Tests string representation of Callstack."""
    assert str(callstack) == (
        "name1 at /home/user/linux/file1:1\n"
        "name2 (macro) at /home/user/linux/src/file2:2"
    )


def test_callstack_as_str_with_rel_paths(callstack):
    """Tests string representation with relative paths of Callstack."""
    assert callstack.as_str_with_rel_paths("/home/user/linux/") == (
        "name1 at file1:1\n"
        "name2 (macro) at src/file2:2"
    )


def test_to_output_yaml_with_rel_path(callstack):
    """Tests YAML representation of Callstack."""
    assert callstack.to_output_yaml_with_rel_path("/home/user/linux/") == [
        {"name": "name1", "file": "file1", "line": 1},
        {"name": "name2 (macro)", "file": "src/file2", "line": 2}
    ]


def test_callstack_get_symbol_names(callstack):
    """Tests function for getting symbols from Callstack."""
    function_names, macro_names, type_names = callstack.get_symbol_names(
        "compared_function")
    assert function_names == {"name1"}
    assert macro_names == {"name2"}
    assert type_names == set()

    callstack2 = Result.Callstack([
        {"name": "struct_name (type)", "file": "file1", "line": 1},
    ])
    *_, type_names2 = callstack2.get_symbol_names(
        "compared_function")
    assert type_names2 == {("struct_name", "compared_function")}

    callstack3 = Result.Callstack([
        {"name": "fun_name", "file": "file1", "line": 1},
        {"name": "struct_name (type)", "file": "file2", "line": 2},
    ])
    *_, type_names3 = callstack3.get_symbol_names(
        "compared_function")
    assert type_names3 == {("struct_name", "fun_name")}


@pytest.fixture
def result(graph):
    result = Result(Result.Kind.NONE, "old-snapshot-path", "new-snapshot-path")

    comp1_result = Result(Result.Kind.NONE, "main_function", "main_function")
    objects_to_compare, *_ = \
        graph.graph_to_fun_pair_list("main_function", "main_function", False)
    for fun_pair in objects_to_compare:
        fun_result = Result(fun_pair[2], "main_function", "main_function")
        fun_result.first = fun_pair[0]
        fun_result.second = fun_pair[1]
        comp1_result.add_inner(fun_result)

    result.add_inner(comp1_result)
    result.graph = graph
    yield result


def test_yaml_output(result, mocker):
    """Tests YAML representation of compare result made by YamlOutput class."""
    mocker.patch("diffkemp.output.get_end_line", return_value=2958)

    # mock relpath to return original path
    def mock_rel_path(path, start):
        return path
    mocker.patch("os.path.relpath", side_effect=mock_rel_path)

    yaml = YamlOutput("/abs/path/to/old-snapshot", "/abs/path/to/new-snapshot",
                      result).output

    assert yaml["old-snapshot"] == "/abs/path/to/old-snapshot"
    assert yaml["new-snapshot"] == "/abs/path/to/new-snapshot"
    assert len(yaml["results"]) == 1

    main_function_result = yaml["results"][0]
    assert main_function_result["function"] == "main_function"
    assert len(main_function_result["diffs"]) == 3
    for diff in main_function_result["diffs"]:
        expected_callstack = []
        if diff["function"] == "___MACRO":
            expected_callstack = [
                {"name": "do_check", "file": "app/main.c", "line": 58},
                {"name": "_MACRO (macro)", "file": "test.c", "line": 1},
                {"name": "__MACRO (macro)", "file": "test.c", "line": 2},
                {"name": "___MACRO (macro)", "file": "test.c", "line": 3}
            ]
        elif diff["function"] == "do_check":
            expected_callstack = [
                {"name": "do_check", "file": "app/main.c", "line": 58},
            ]
        elif diff["function"] == "struct_file":
            expected_callstack = [
                {"name": "do_check", "file": "app/main.c", "line": 58},
                {"name": "struct_file (type)", "file": "include/file.h",
                 "line": 121},
            ]
        assert diff["old-callstack"] == expected_callstack
        assert diff["new-callstack"] == expected_callstack

    # note: definitions does not currently include macros
    assert len(yaml["definitions"]) == 3
    for name, definition in yaml["definitions"].items():
        if name == "main_function":
            def_info = {
                "line": 51, "file": "app/main.c", "end-line": 2958
            }
            assert definition == {
                "kind": "function", "old": def_info, "new": def_info
            }
        elif name == "do_check":
            def_info = {"line": 105, "file": "app/main.c", "end-line": 2958}
            assert definition == {
                "kind": "function", "old": def_info, "new": def_info
            }
        elif name == "struct_file":
            def_info = {
                "line": 121, "file": "include/file.h", "end-line": 2958
            }
            assert definition == {
                "kind": "type", "old": def_info, "new": def_info
            }


@pytest.fixture
def mock_files_content(mocker):
    """Mock open function to return specified content as content of files."""
    def inner(content):
        mocked_open = mocker.mock_open(read_data=content)
        mocker.patch("builtins.open", mocked_open)
    return inner


def test_end_line_for_function(mock_files_content):
    """Testing getting correct end line for function."""
    mock_files_content(
        "// empty line\n"
        "int dev_queue_xmit(struct sk_buff *skb)\n"
        "{\n"
        "       return __dev_queue_xmit(skb, NULL);\n"
        "}\n"
        "void foo() {}\n")
    assert get_end_line("file", 2, "function") == 5


def test_end_line_for_type(mock_files_content):
    """Testing getting correct end line for type (struct)."""
    mock_files_content(
        "struct foo {\n"
        "       unsigned bar;\n"
        "};\n"
        "void baz() {}\n")
    assert get_end_line("file", 1, "type") == 3


def test_end_line_for_macro(mock_files_content):
    """Testing getting correct end line for macro."""
    mock_files_content(
        "void foo() {}\n"
        "// empty line\n"
        "#define __this_cpu_read(pcp)                    \\\n"
        "({                                              \\\n"
        "       __this_cpu_preempt_check(\"read\");      \\\n"
        "       raw_cpu_read(pcp);                       \\\n"
        "})\n")
    assert get_end_line("file", 3, "macro") == 7
