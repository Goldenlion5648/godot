import argparse
import base64
import re
import sys
import traceback

SNIPPET_START_INDICATOR_WITH_AT_SIGN = "@snippet_start"
SNIPPET_END_INDICATOR_WITH_AT_SIGN = "@snippet_end"
INSERT_SNIPPET_SYMBOL = "!!"
SOURCE_LINE_COMMENT = "##SOURCE_LINE:"


def get_params_from(to_read: str):
    to_read = to_read.removeprefix("(").removesuffix(")")
    return re.split(r",\s+", to_read)


class SnippetData:
    def __init__(self, name, lines, param_names):
        self.name = name
        self.lines = lines
        self.param_names = param_names

    def get_content_with_values_inserted(self, arg_values):
        param_name_to_value = dict(zip(self.param_names, arg_values))
        ret = "\n".join(self.lines)
        for name, value in param_name_to_value.items():
            ret = ret.replace(name, value)
        return ret.split("\n")

    def __repr__(self):
        params_joined = " ".join(self.param_names)
        lines_joined = "\n".join(self.lines)
        return f"NAME: {self.name}\nPARAMS: {params_joined}\nLINES:\n{lines_joined}\n\n"


class MacroRunner:
    def __init__(self, data):
        self.line_num = 0
        self.output = []
        self.data = data

    def add_to_output(self, content):
        self.output.append(f"{content} {SOURCE_LINE_COMMENT}{self.line_num + 1}")

    def get_processed_lines(self):
        lines = data.splitlines()
        self.line_num = 0
        self.output = []
        snippet_name_to_data: dict[str, SnippetData] = {}
        while self.line_num < len(lines):
            line = lines[self.line_num]
            # finds the macro definition
            if line.startswith(SNIPPET_START_INDICATOR_WITH_AT_SIGN):
                params = get_params_from(line.removeprefix(SNIPPET_START_INDICATOR_WITH_AT_SIGN))
                snippet_name = params.pop(0)
                self.add_to_output(f"# started {snippet_name}")
                self.line_num += 1
                line = lines[self.line_num]
                snippet_lines = []
                while not line.startswith("@snippet_end"):
                    snippet_lines.append(line)
                    self.add_to_output(f"# ate part of snippet {snippet_name}")
                    self.line_num += 1
                    line = lines[self.line_num]
                cur_snippet_data = SnippetData(snippet_name, snippet_lines, params)
                snippet_name_to_data[snippet_name] = cur_snippet_data
                # print("added snippet:\n", cur_snippet_data)
                self.add_to_output(f"# ended snippet {snippet_name}")
            else:
                # insert the macro
                should_insert_whitespace_prefix = True
                had_snippet_to_insert_into = False
                col = 0
                line_starting_whitespace = found.group() if (found := re.search(r"^\s+", line)) is not None else ""
                while col < len(line):
                    if col + 1 < len(line) and line[col : col + len(INSERT_SNIPPET_SYMBOL)] == INSERT_SNIPPET_SYMBOL:
                        part_before_snippet = line[:col]
                        col += len(INSERT_SNIPPET_SYMBOL)
                        had_snippet_to_insert_into = True
                        snippet_name = re.search(r"\w+", line[col:]).group()
                        col += len(snippet_name)
                        arg_values = get_params_from(line[col:])

                        cur_snippet_data_for_insertion = snippet_name_to_data[snippet_name]
                        lines_with_values = cur_snippet_data_for_insertion.get_content_with_values_inserted(arg_values)
                        if should_insert_whitespace_prefix:
                            lines_with_values = [line_starting_whitespace + line for line in lines_with_values]
                        else:
                            lines_with_values[0] = part_before_snippet + lines_with_values[0]
                            # lines_with_values = [part_before_snippet + line for line in lines_with_values]
                        for found_line in lines_with_values:
                            self.add_to_output(found_line)

                    if not line[col].isspace():
                        should_insert_whitespace_prefix = False

                    col += 1

                if not had_snippet_to_insert_into:
                    self.add_to_output(f"{line}")
            self.line_num += 1
        return self.output


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
        if IN_DEBUG:
            testing_args = [
                ("--base64_input_string"),
                "CiMgdGhpcyBydW5zIG9uIGEgc2luZ2xlIGxpbmUKIyBAbW9kaWZ5KHNhdmVfdG9fZGlzaykKIyB2YXIgaGVhbHRoID0gMTAKCgpAc25pcHBldF9zdGFydChjYW5jZWxfb3V0KQppZiB0ZXN0ID09IC0xOgoJcmVzZXQoKQoJcmV0dXJuCkBzbmlwcGV0X2VuZAoKQHNuaXBwZXRfc3RhcnQoY2FuY2VsX291dF92MiwgJGJhZF92YWx1ZSkKaWYgdGVzdCA9PSAkYmFkX3ZhbHVlOgoJcmVzZXQoKQoJcmV0dXJuCkBzbmlwcGV0X2VuZAoKQHNuaXBwZXRfc3RhcnQobnVtYmVyc194eXosICR4LCAkeSwgJHopCiR4ICogJHggKiAkeCArICR5ICsgJHoKQHNuaXBwZXRfZW5kCgoKZnVuYyBkb19zdHVmZih0ZXN0KToKCSEhY2FuY2VsX291dCgpCgkhIWNhbmNlbF9vdXRfdjIoLTk5OSkKCXByaW50KCEhbnVtYmVyc194eXooNSwgOCwgOSkpCgkKZnVuYyBub3JtYWxfZnVuYygpOgoJcHJpbnQoInRoZSBlbmQiKQoJCgo=",
                ("--output_file_path"),
                ("/home/golden/Documents/programming/prs/godot/compiler_output.gd"),
            ]
            args = parser.parse_args(testing_args)
        else:
            args = parser.parse_args()
        output_file = args.output_file_path if args.output_file_path else (args.input_file_path + ".processed")
        if args.base64_input_string:
            data = args.base64_input_string
            data = base64.b64decode(data).decode()
        else:
            with open(args.input_file_path) as f:
                data = f.read()
        if IN_DEBUG:
            print(data)
        runner = MacroRunner(data)
        lines_with_replacements_done = runner.get_processed_lines()

        with open(output_file, "w") as f:
            print("#", args, file=f)
            print("#", sys.argv, file=f)
            for line in lines_with_replacements_done:
                print(line, file=f)
        # print("#", args)
        # print("#", sys.argv)
        for line in lines_with_replacements_done:
            print(line)
    except Exception:
        to_show = traceback.format_exc()
        print(to_show)
        # with open(output_file) as crash_file:
        #     crash_file.write(to_show)
