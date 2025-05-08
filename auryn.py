# cli_pipeline_interpreter.py

import subprocess
import json
import time
import shlex
import re
from pathlib import Path
from itertools import product

NAMED_STREAMS = {}
CONSTANTS = {}
PARSER_DIR = Path("parsers")
DEBUG = False


def run_command(command):
    if command.strip() == "cat":
        print(f"[WARNING] Command 'cat' detected with no input redirection. This will hang. Skipping execution.")
        return "", 1
    print(f"[RUNNING] {command}")
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    output = []
    for line in process.stdout:
        line = line.rstrip()
        print(line)
        output.append(line)
    process.wait()
    return "\n".join(output), process.returncode


def apply_parser(parser_name, input_text):
    parser_script = PARSER_DIR / f"{parser_name.lower()}.sh"
    if not parser_script.exists():
        raise FileNotFoundError(f"Parser script not found: {parser_script}")
    if DEBUG:
        print(f"[DEBUG] Running parser '{parser_name}' with input:\n{input_text}\n")
    process = subprocess.Popen(
        ["bash", str(parser_script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    stdout, stderr = process.communicate(input=input_text)
    if process.returncode != 0:
        print(f"[ERROR] Parser '{parser_name}' failed:\n{stderr}")
        return []
    parsed_lines = stdout.strip().splitlines()
    if DEBUG:
        print(f"[DEBUG] Parser output ({len(parsed_lines)} lines):\n" + "\n".join(parsed_lines))
    return parsed_lines


def append_to_file(filepath, lines):
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "a") as f:
        for line in lines:
            f.write(line + "\n")


def parse_run_components(block):
    match = re.match(r'^run\s+"(.+?)"', block)
    if not match:
        return None, None, None, None
    command_part = match.group(1)
    parser_name = re.search(r'parsewith\s+(\S+)', block)
    output_file = re.search(r'output\s+"(.+?)"', block)
    stream_name = re.search(r'as\s+(\$\w+)', block)
    return (
        command_part,
        parser_name.group(1) if parser_name else None,
        output_file.group(1) if output_file else None,
        stream_name.group(1)[1:] if stream_name else None
    )


def extract_command_from_body(body):
    cmd_match = re.search(r'(["\'])(.*?)\1', body)
    if not cmd_match:
        raise ValueError("Command block must be wrapped in matching ' or \" quotes.")
    quote_type = cmd_match.group(1)
    command = cmd_match.group(2)
    remaining = body.replace(cmd_match.group(0), "", 1)
    if quote_type == "'" and ("$" in command or "{line}" in command):
        raise ValueError("Literal command block in single quotes cannot contain variables or {line} interpolation.")
    return command, quote_type, remaining


def apply_constants(text):
    for _ in range(10):
        old_text = text
        for key, val in CONSTANTS.items():
            text = text.replace(f"__{key}__", val)
        if text == old_text:
            break
    else:
        raise ValueError("Potential circular constant reference detected.")
    return text


def resolve_constant_value(val):
    resolved = apply_constants(val)
    if "__" in resolved:
        raise ValueError(f"Unresolved constant reference in value: {val}")
    return resolved


def interpret_dsl(lines):
    has_seen_non_constant_line = False
    logical_lines = []
    current = ""
    for line in lines:
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(" ") or line.startswith("\t"):
            current += " " + line.strip()
        else:
            if current:
                logical_lines.append(current)
            current = line.strip()
    if current:
        logical_lines.append(current)

    for line in logical_lines:
        if line.startswith("__") and "=" in line:
            if has_seen_non_constant_line:
                raise ValueError("Constants must be declared before all other DSL instructions.")
            const_name, const_val = map(str.strip, line.split("=", 1))
            const_name = const_name.strip("_")
            const_val = const_val.strip('"')
            resolved_val = resolve_constant_value(const_val)
            CONSTANTS[const_name] = resolved_val
            if DEBUG:
                print(f"[DEBUG] Defined constant {const_name} = {resolved_val}")
            if const_name == "OUTPUT_DIR":
                Path(resolved_val).mkdir(parents=True, exist_ok=True)
                if DEBUG:
                    print(f"[DEBUG] Ensured directory exists for OUTPUT_DIR: {resolved_val}")
            continue

        has_seen_non_constant_line = True
        line = apply_constants(line)

        if line.startswith("run"):
            command_part, parser_name, output_file, stream_name = parse_run_components(line)
            if not command_part:
                print(f"[ERROR] Could not parse line: {line}")
                continue
            output, code = run_command(command_part)
            if code != 0:
                print(f"[ERROR] Command failed: {command_part}")
                continue
            parsed = apply_parser(parser_name, output) if parser_name else output.strip().splitlines()
            if stream_name:
                NAMED_STREAMS[stream_name] = parsed
                if DEBUG:
                    print(f"[DEBUG] Stored output in variable '{stream_name}'\n")
            if output_file:
                append_to_file(output_file, parsed)
                if DEBUG:
                    print(f"[DEBUG] Appended output to file '{output_file}'\n")

        elif line.startswith("map"):
            header, body = line.split(" do ", 1)
            inputs = re.findall(r'\$(\w+)', header)
            command_part, quote_type, after_command = extract_command_from_body(body)
            out_name = parser_name = output_file = None
            if "parsewith" in after_command:
                parser_name = re.search(r'parsewith\s+(\S+)', after_command).group(1)
            if "output" in after_command:
                output_match = re.search(r'output\s+"(.+?)"', after_command)
                if not output_match:
                    raise ValueError(f"Output path must be quoted properly: {line}")
                output_file = output_match.group(1)
            if "as" in after_command:
                out_name = re.search(r'as\s+(\$\w+)', after_command).group(1)[1:]
            input_lists = [NAMED_STREAMS.get(name, []) for name in inputs]
            all_combinations = product(*input_lists)
            collected = []
            for combo in all_combinations:
                cmd = command_part
                if quote_type == '"':
                    for i, val in enumerate(combo):
                        cmd = cmd.replace(f"${inputs[i]}", val).replace("{line}", val)
                output, code = run_command(cmd)
                if code != 0:
                    print(f"[ERROR] Command failed: {cmd}")
                    continue
                collected.append(output)
            if parser_name:
                collected = apply_parser(parser_name, "\n".join(collected))
            if out_name:
                NAMED_STREAMS[out_name] = collected
                if DEBUG:
                    print(f"[DEBUG] Stored output in variable '{out_name}'\n")
            if output_file:
                append_to_file(output_file, collected)
                if DEBUG:
                    print(f"[DEBUG] Appended output to file '{output_file}'\n")

        elif line.startswith("input"):
            match = re.match(r'input\s+"(.+?)"\s+map\s+(.*?)\s+do\s+(.*)', line)
            if not match:
                raise ValueError(f"Malformed input-map block: {line}")
            file_path, varlist, tail = match.groups()
            lines_in_file = Path(file_path).read_text().splitlines()
            line_stream_name = f"_input_{file_path}"
            NAMED_STREAMS[line_stream_name] = lines_in_file
            line = f"map ${line_stream_name} {varlist} do {tail}"
            interpret_dsl([line])


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python cli_pipeline_interpreter.py <dsl-file> [--debug]")
        sys.exit(1)

    dsl_file = sys.argv[1]
    if len(sys.argv) > 2 and sys.argv[2] == "--debug":
        DEBUG = True

    with open(dsl_file) as f:
        dsl_lines = f.readlines()

    interpret_dsl(dsl_lines)
