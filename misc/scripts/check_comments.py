#!/usr/bin/env python3

if __name__ != "__main__":
    raise SystemExit(f'Utility script "{__file__}" should not be used as a module!')

import argparse
import re
import subprocess
import sys

sys.path.insert(0, "./")

try:
    from methods import print_error
except ImportError:
    raise SystemExit(f"Utility script {__file__} must be run from repository root!")


EXTENSIONS = (".cpp", ".cc", ".h", ".hpp")

single_line_comment = re.compile(r"//(.*)$")
multi_line_comment = re.compile(r"/\*(.*?)\*/", re.DOTALL)


def validate_comment(comment, file, line_num, check_capital=True, check_period=True):
    comment = comment.strip()

    if not comment:
        return []

    errors = []

    if not comment[0].isupper() and check_capital:
        errors.append(f"{file}:{line_num} - Comment should start with a capital letter:\n{comment}")

    if not comment.endswith(".") and check_period:
        errors.append(f"{file}:{line_num} - Comment should end with a period:\n{comment}")

    return errors


def check_file(filepath):
    errors = []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return [f"{filepath}: Failed to read file ({e})"]

    # Single-line comments
    previous_comment_line = -10
    line_num_to_comment = {}
    for i, line in enumerate(content.splitlines(), start=1):
        match = single_line_comment.search(line)
        if match and "/*" not in line:
            print(line)
            line_num_to_comment[i] = line
            should_have_capital = i - previous_comment_line >= 2
            should_have_period = (i - 1) not in line_num_to_comment

            errors.extend(validate_comment(match.group(1), filepath, i, should_have_capital, should_have_period))

    # # Multi-line comments
    # for match in multi_line_comment.finditer(content):
    #     comment = match.group(1)
    #     line_num = content[:match.start()].count("\n") + 1
    #     errors.extend(validate_comment(comment, filepath, line_num))

    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Validate that C++ comments start with a capital letter and end with a period"
    )
    parser.add_argument("files", nargs="+", help="A list of files to check")
    args = parser.parse_args()

    cmd = ["git", "diff", "--cached", "-U0", "--", "path/to/file.cpp"]

    changed_lines = subprocess.run(cmd, capture_output=True, text=True)
    print(changed_lines)
    return 1
    ret = 0

    for file in args.files:
        if not file.endswith(EXTENSIONS):
            continue

        errors = check_file(file)
        for err in errors:
            print_error(err)

        ret += len(errors)

    return ret


try:
    raise SystemExit(main())
except KeyboardInterrupt:
    import os
    import signal

    signal.signal(signal.SIGINT, signal.SIG_DFL)
    os.kill(os.getpid(), signal.SIGINT)
