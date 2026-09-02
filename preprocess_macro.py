import argparse
import re
import sys
import traceback

SNIPPET_START_INDICATOR_WITH_AT_SIGN = "@snippet_start"
SNIPPET_END_INDICATOR_WITH_AT_SIGN = "@snippet_end"
INSERT_SNIPPET_SYMBOL = "!!"
SOURCE_LINE_COMMENT = "##SOURCE_LINE:"
MACRO_DEFINED_AT_COMMENT = "##DEFINED_AT:"
MACRO_NAME_AND_DEFINED_DELIMETER = ">"
OPERATE_ON_EACH_LINE_WITH_AT_SIGN = "@each"


def get_params_from(to_read: str):
    # print()
    # print(to_read)
    part_in_parenthesis = re.search(r"\((.+)\)", to_read)
    # print(part_in_parenthesis)
    # print(part_in_parenthesis.group(1))
    if not part_in_parenthesis:
        return ["XXX"]
    to_read = part_in_parenthesis.group(1)
    # to_read = to_read.removeprefix("(").removesuffix(")")
    return re.split(r",\s*", to_read)


class SnippetData:
    def __init__(self, name, lines, param_names, defined_at_line_num, file_defined_in, does_operate_on_each_line=False):
        self.name = name
        self.lines = lines
        self.param_names = param_names
        self.defined_at_line_num = defined_at_line_num
        self.file_defined_in = file_defined_in
        self.does_operate_on_each_line = does_operate_on_each_line

    def get_lines_with_values_inserted(self, arg_values):
        default_macros_to_lamba = {
            "$LINE_NUM": lambda: str(len(runner.output) + 1),
            "$params": lambda: " ".join(arg_values),
        }
        print("self.param_names", self.param_names)
        print("arg_values", arg_values)
        param_name_to_value = dict(zip(self.param_names, arg_values))
        print("param_name_to_value", param_name_to_value)
        for default, func in default_macros_to_lamba.items():
            param_name_to_value[default] = func()
        ret = "\n".join(self.lines)
        ret = re.sub(r"(\$\w+)\b", lambda found: param_name_to_value[found.group()], ret)
        return ret.split("\n")

    def get_definition_print_out(self):
        return f"#{self.name}{MACRO_NAME_AND_DEFINED_DELIMETER}{MACRO_DEFINED_AT_COMMENT}{self.defined_at_line_num}"

    # def print_simple(self):
    #     return ", ".join(x if type(x) == str else ""vars(self).values())

    def __repr__(self):
        params_joined = " ".join(self.param_names)
        lines_joined = "\n".join(self.lines)
        return f"""NAME: {self.name}
PARAMS: {params_joined}
LINES:
{lines_joined}
DEFINED_AT:{self.defined_at_line_num}
RUNS ON EACH LINE:{self.does_operate_on_each_line}

"""


class MacroRunner:
    def __init__(self, data: str, file_name_with_dot_gd: str):
        self.line_num = 0
        self.file_name_with_dot_gd = file_name_with_dot_gd
        self.output: list[str] = []
        self.errors: list[str] = []
        self.data = data
        self.snippet_name_to_data: dict[str, SnippetData] = {}

    def get_final_output_lines(self):
        return self.output + self.get_macro_lines()

    def get_macro_lines(self):
        return [data.get_definition_print_out() for data in self.snippet_name_to_data.values()]

    def add_to_output(self, content):
        self.output.append(f"{content} {SOURCE_LINE_COMMENT}{self.line_num + 1}")

    def show_snippets(self):
        for snippet_data in self.snippet_name_to_data.values():
            print(snippet_data)

    def calculate_processed_lines(self):
        lines = self.data.splitlines()
        if INSERT_SNIPPET_SYMBOL not in self.data:
            return lines
        self.line_num = 0
        self.output = []
        while self.line_num < len(lines):
            line = lines[self.line_num]
            is_normal_snippet = line.startswith(SNIPPET_START_INDICATOR_WITH_AT_SIGN)
            is_an_each_line = line.startswith(OPERATE_ON_EACH_LINE_WITH_AT_SIGN)
            # finds the macro definition
            if is_normal_snippet or is_an_each_line:
                params = get_params_from(line)
                snippet_name = params.pop(0)
                self.add_to_output(f"# started {snippet_name}")
                self.line_num += 1
                line = lines[self.line_num]
                snippet_lines = []
                snippet_starting_line = self.line_num
                while not line.startswith("@snippet_end") and not line.startswith("@each_end"):
                    snippet_lines.append(line)
                    self.add_to_output(f"# ate part of snippet {snippet_name}")
                    self.line_num += 1
                    line = lines[self.line_num]
                cur_snippet_data = SnippetData(
                    snippet_name,
                    snippet_lines,
                    params,
                    snippet_starting_line,
                    self.file_name_with_dot_gd,
                    is_an_each_line,
                )
                self.snippet_name_to_data[snippet_name] = cur_snippet_data
                # print("added snippet:\n", cur_snippet_data)
                self.add_to_output(f"# ended snippet {snippet_name}")
            else:
                # insert the macro
                pos_for_insert = line.find(INSERT_SNIPPET_SYMBOL)
                if pos_for_insert == -1:
                    self.add_to_output(f"{line}")
                    self.line_num += 1
                    continue
                line_starting_whitespace = found.group() if (found := re.search(r"^\s+", line)) is not None else ""
                part_before_snippet = line[:pos_for_insert]
                snippet_name = re.search(r"\w+", line[pos_for_insert + len(INSERT_SNIPPET_SYMBOL) :]).group()
                if snippet_name not in self.snippet_name_to_data:
                    self.errors.append(f"Unknown macro: '{snippet_name}'")
                    break
                cur_snippet = self.snippet_name_to_data[snippet_name]
                print(cur_snippet_data)
                if cur_snippet.does_operate_on_each_line:
                    self.line_num += 1
                    lines_with_values = []
                    while self.line_num < len(lines) and not lines[self.line_num].startswith("!!end"):
                        arg_values = lines[self.line_num].split()
                        print(arg_values)
                        lines_with_values.extend(cur_snippet.get_lines_with_values_inserted(arg_values))
                        self.line_num += 1
                else:
                    arg_values = get_params_from(line)
                    lines_with_values = cur_snippet.get_lines_with_values_inserted(arg_values)
                    if pos_for_insert > 0:
                        lines_with_values = [line_starting_whitespace + line for line in lines_with_values]
                    else:
                        # it was a single line snippet like !!compute_equation
                        lines_with_values[0] = part_before_snippet + lines_with_values[0]

                    # lines_with_values = [part_before_snippet + line for line in lines_with_values]
                for found_line in lines_with_values:
                    self.add_to_output(found_line)

                # if not line[col].isspace():
                #     should_insert_whitespace_prefix = False

                # col += 1

                # if not found_snippet_to_insert_into:
                #     self.add_to_output(f"{line}")
            self.line_num += 1


# if False:
#     with open("/home/golden/Documents/programming/prs/godot/called_at.txt", "w") as f:
#         f.write(str(datetime.now()))
#         f.write("\n")
#         f.write("\n".join(f"{i}: {sys.argv[i]}" for i in range(len(sys.argv))))
#         try:
#             args = parser.parse_args()
#         except Exception as e:
#             f.write(e)
#             exit(1)
#         f.write("\n" + str(args))


# print("#", args)
# print("#", sys.argv)
# with open(args.output_file_path, "w") as f:
#     f.write("random")
#     print("wrote to", args.output_file_path)
if __name__ == "__main__":
    try:
        IN_DEBUG = "test_mode" in sys.argv
        parser = argparse.ArgumentParser()
        parser.add_argument("--input_file_path", type=str)
        parser.add_argument("--output_file_path", type=str)
        parser.add_argument("--base64_input_string", type=str)
        parser.add_argument("macros", type=bool, nargs="?")
        args = parser.parse_args()
        output_file = args.output_file_path if args.output_file_path else (args.input_file_path + ".processed")
        # if args.base64_input_string:
        #     data = args.base64_input_string
        #     data = base64.b64decode(data).decode()
        # else:
        with open(args.input_file_path) as f:
            data_read = f.read()
        if IN_DEBUG:
            print(data_read)
        runner = MacroRunner(data_read, args.input_file_path)
        runner.calculate_processed_lines()
        lines_with_replacements_done = runner.get_final_output_lines()
        if "macros" in sys.argv:
            runner.show_snippets()
            exit()

        with open(output_file, "w") as f:
            # print("#", args, file=f)
            # print("#", sys.argv, file=f)
            if runner.errors:
                for line in runner.errors:
                    print(line, file=f)
            else:
                for line in lines_with_replacements_done:
                    print(line, file=f)
        # print("#", args)
        # print("#", sys.argv)
        for line in lines_with_replacements_done:
            print(line)
    except Exception:
        to_show = traceback.format_exc()
        print(to_show)
        with open(output_file, "w") as crash_file:
            crash_file.write(to_show)
