import subprocess
import os
import os
from pathlib import Path
from urllib.parse import urlparse, unquote

opened_uris = {}

def Read(file_path : str) :
    if os.path.isdir(file_path):
        try:
            files = os.listdir(file_path)
            return f"Directory '{file_path}' contains:\n" + "\n".join(files)
        
        except Exception as e:
            return f"Error on Opening Directory  : {e}"

    if os.path.isfile(file_path):
        try:
            with open(file_path, "r") as file:
                return file.read()
        
        except Exception as e:
            return f"Error on File Directory  : {e}"

    return "Error : Path is not found"

def Write(file_path : str, content : str):
    with open(f"{file_path}", "w") as file:
        file.write(content)

    path_ = Path(file_path).resolve()
    uri = path_.as_uri()

    operation = "textDocument/didChange" if uri in opened_uris else "textDocument/didOpen"
    version = opened_uris.get(uri, 0) + 1
    opened_uris[uri] = version

    client.notify(operation, {
        "textDocument": {
        "uri": uri,
        "languageId": "python",
        "version": version,
        "text": content
        }
    })


def Bash(command : str):
    res = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if res.returncode == 0:
        return res.stdout
    else:
        return res.stderr

def LSP(operation: str, filePath: str, line: int, character: int):
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

    path_ = Path(filePath).resolve()
    uri = path_.as_uri()

    if uri not in opened_uris:

        content = path_.read_text()
        client.notify("textDocument/didOpen", {
            "textDocument": {
            "uri": uri,
            "languageId": "python",
            "version": 1,
            "text": content
            }
        })

        opened_uris[uri] = 1

    if operation == "goToDefinition":

        res = client.request("textDocument/definition",{
            "textDocument": { "uri": uri },
            "position": { "line": line - 1, "character": character - 1 }
        })

        if not res:
            return "Definition Not Found"

        file_path, start_line, start_char = extract_path_start_line_char(res)        
        return f"Defined in {file_path}:{start_line}:{start_char}"

    elif operation == "findReferences":
        res = client.request("textDocument/references",{
            "textDocument": { "uri": uri },
            "position": { "line": line - 1, "character": character - 1 },
            "context": { "includeDeclaration": True }
        })

        if not res:
            return "Definition Not Found"

        file_refrences = {}
        for file in res:
            path, line_, char_ = extract_path_start_line_char(file)
            file_refrences.setdefault(path, []).append(f"Line {line_}:{char_}")

        final_string = [f"Found {len(res)} references across {len(file_refrences)} files:\n"]
        for path in file_refrences:
            final_string.append(path)
            final_string.extend(file_refrences[path])
            final_string.append("\n")

        return "\n".join( final_string[:-1] )