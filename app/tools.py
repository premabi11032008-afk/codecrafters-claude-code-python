import subprocess
import os

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