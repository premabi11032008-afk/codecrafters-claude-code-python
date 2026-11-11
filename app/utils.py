from pathlib import Path
from urllib.parse import urlparse, unquote

def uri_to_path(uri: str) -> str:
    parsed = urlparse(uri)
    abs_path = Path(unquote(parsed.path))
    try:
        return str(abs_path.relative_to(Path.cwd()))
    except ValueError:
        return str(abs_path)

def extract_path_start_line_char(arg: dict):
    file_path = uri_to_path(arg.get("uri", ""))
    start_coords = arg.get("range").get("start")

    start_line = start_coords.get("line") + 1
    start_char = start_coords.get("character") + 1

    return file_path, start_line, start_char

