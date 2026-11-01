def READ(path : str) :
    with open(f"{path}", "r") as file:
        print( file.read() )