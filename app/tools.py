import subprocess

def Read(file_path : str) :
    with open(f"{file_path}", "r") as file:
        content = file.read() 

    return  content

def Write(file_path : str, content : str):
    with open(f"{file_path}", "w") as file:
        file.write(content)

def Bash(command : str):
    res = subprocess.run(command.split(), capture_output=True )
    return res