import subprocess
import os
import os
from pathlib import Path
from urllib.parse import urlparse, unquote
from .lsp_client import LSPClient

opened_uris = set()

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

def Bash(command : str):
    res = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    if res.returncode == 0:
        return res.stdout
    else:
        return res.stderr

def LSP(operation: str, filePath: str, line: int, character: int):
    client = LSPClient.from_environment()

    def uri_to_path(uri: str) -> str:
        parsed = urlparse(uri)
        abs_path = Path(unquote(parsed.path))
        try:
            return str(abs_path.relative_to(Path.cwd()))
        except ValueError:
            return str(abs_path)

    if operation == "goToDefinition":

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

            opened_uris.add(uri)

        res = client.request("textDocument/definition",{
            "textDocument": { "uri": uri },
            "position": { "line": line - 1, "character": character - 1 }
        })

        if not res:
            return "Definition Not Found"

        if isinstance(res, list):
            res = res[0]

        file_path = uri_to_path(res.get("uri", ""))
        start_coords = res.get("start", {})

        start_line = start_coords.get("line") + 1
        start_char = start_coords.get("character") + 1

        return f"Defined in {file_path}:{start_line}:{start_char}"