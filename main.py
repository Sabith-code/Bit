import argparse
import json
import sys
from pathlib import Path
class Repository:
    def __init__(self, path="."):
        self.path = Path(path).resolve()
        self.bit_dir = self.path / ".bit"

        #.bit/objects
        self.objects_dir = self.bit_dir / "objects"
        
        # .bit/refs
        self.ref_dir = self.bit_dir / "refs"
        self.heads_dir = self.ref_dir / "heads"

        # Head file
        self.head_file = self.bit_dir / "HEAD"

        # .bit/index
        self.index_file = self.bit_dir / "index"
    def init(self)-> bool:
        if self.bit_dir.exists():
            return False
        #create directories
        self.bit_dir.mkdir()
        self.objects_dir.mkdir()
        self.ref_dir.mkdir()
        self.heads_dir.mkdir()
    
        #create initial HEAD pointing to a branch
        self.head_file.write_text("ref: refs/heads/master\n")

        self.index_file.write_text(json.dumps({},indent=2))
        print(f"Initalized empyt Bit repository in {self.bit_dir}")
        return True
        


def main():
    parser = argparse.ArgumentParser(
        description="Bit - A simple version of Git"
    )
    subparsers = parser.add_subparsers(
        dest = "command",
        help = "Available commands"
    )
    
    #init command
    init_parser = subparsers.add_parser("init", help="Initialize a new repository")
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    try:
        if args.command == "init":
            repo = Repository()
            if not repo.init():
                print("Repository alreaady exists")
                return

    except Exception as e:
        print(f"Error {e}")
        sys.exit(1)
main()