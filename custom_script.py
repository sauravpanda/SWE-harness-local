import os

def print_directory_tree(path, indent=0):
    """
    Print the directory tree of the given path.
    """
    for entry in os.listdir(path):
        entry_path = os.path.join(path, entry)
        is_dir = os.path.isdir(entry_path)
        prefix = "│   " * indent + ("├── " if is_dir else "└── ")
        print(prefix + entry)
        if is_dir:
            print_directory_tree(entry_path, indent + 1)

if __name__ == "__main__":
    print_directory_tree(".")