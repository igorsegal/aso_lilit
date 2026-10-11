"""Read-only language-aware source inspection for ASO Lilit.

Never runs supplied project code. Compilation of C++ uses stdin only and
requires an explicit available compiler; MQL4 is not treated as C++.
"""
import ast
import re
import shutil
import subprocess
from pathlib import Path

EXTENSIONS = {
    ".py": "python", ".cpp": "cpp", ".cc": "cpp", ".cxx": "cpp",
    ".hpp": "cpp", ".hh": "cpp", ".h": "cpp",
    ".mq4": "mql4", ".mqh": "mql4",
}
MAX_BYTES = 1_000_000

def inspect_source(path: Path, run_cpp_compiler: bool = False) -> dict:
    language = EXTENSIONS.get(path.suffix.lower())
    if language is None:
        raise ValueError("Unsupported source extension")
    if path.is_symlink() or not path.is_file():
        raise ValueError("Source must be a regular file")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Source file too large")
    source = path.read_text(encoding="utf-8-sig", errors="strict")
    base = {"language": language, "file": path.name, "executed": False, "diagnostics": []}
    if language == "python":
        try:
            ast.parse(source, filename=path.name)
            return {**base, "status": "PASS", "check": "python_ast_parse"}
        except SyntaxError as error:
            return {**base, "status": "FAIL", "check": "python_ast_parse",
                    "diagnostics": [f"line {error.lineno}: {error.msg}"]}
    if language == "mql4":
        return {**base, "status": "NOT_VERIFIED", "check": "requires_metaeditor",
                "diagnostics": ["MQL4 compilation requires MetaEditor; C++ compilers are not substitutes."]}
    if not run_cpp_compiler:
        return {**base, "status": "NOT_VERIFIED", "check": "cpp_compiler_not_requested",
                "diagnostics": ["C++ compilation not requested."]}
    compiler = shutil.which("clang++") or shutil.which("g++")
    if compiler is None:
        return {**base, "status": "NOT_VERIFIED", "check": "cpp_compiler_unavailable",
                "diagnostics": ["No clang++ or g++ available."]}
    # No filesystem output and no shell. The project source is piped via stdin.
    # Compilation is an opt-in action; not enabled for untrusted project files by default.
    try:
        result = subprocess.run([compiler, "-x", "c++", "-std=c++17", "-fsyntax-only", "-"],
                                input=source, capture_output=True, text=True,
                                timeout=15, shell=False)
    except subprocess.TimeoutExpired:
        return {**base, "status": "FAIL", "check": "cpp_syntax",
                "diagnostics": ["Compiler timed out"]}
    return {**base, "status": "PASS" if result.returncode == 0 else "FAIL",
            "check": "cpp_syntax", "diagnostics": ([result.stderr[:3000]] if result.stderr else [])}
