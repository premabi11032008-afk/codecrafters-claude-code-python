def Read(file_path : str) :
    with open(f"{file_path}", "r") as file:
        content = file.read() 

    return  content