def Read(file_path : str) :
    with open(f"{path}", "r") as file:
        print( file.read() )