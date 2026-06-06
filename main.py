from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Dict
import zlib

class BitObjects:
    def __init__(self, obj_type: str, content: bytes):  #obj_type = blob, tree, commit
        self.type =obj_type
        self.content = content
    def hash(self) -> str:
        # hash format: f(<type> <size>|0<content)
        header = f"{self.type} {len(self.content)}\0".encode() #encode converts to bytes format, \0 is an null indes which is used to differentiate dfferent things
        return hashlib.sha1(header + self.content).hexdigest() #encode it using sha1 and return as string of hexadecimal values
    
    def serialize(self) -> bytes: #lossless compression of file content
        header = f"{self.type} {len(self.content)}\0".encode() #encode converts to bytes format
        return zlib.compress(header + self.content)
    @classmethod             #we use class method when we dont want to use any variables/instances of the  class such as self.path etc. we dont care about existing instances and want to use an entirely new instance thats when we use classmethod
    def deserialize(cls, data:bytes) -> BitObjects:
        decompressed = zlib.decompress(data)
        null_idx = decompressed.find(b"\0")
        header = decompressed[:null_idx]
        content = decompressed[null_idx + 1:]

        obj_type, size = header.split(b" ") #split by space

        return cls(obj_type, content)
    
class Blob(BitObjects): #just store the content
    def __init__(self, content):
        super().__init__("blob", content)
    def get_content(self) -> bytes:
        return self.content
    
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
        self.save_index({})
        print(f"Initalized empyt Bit repository in {self.bit_dir}")
        return True
    
    def store_objects(self, obj: BitObjects) -> str:
        obj_hash = obj.hash()
        obj_dir = self.objects_dir / obj_hash[:2] #first 2 characters of the hash
        obj_file = obj_dir / obj_hash[2:] #remaining characters of the hash
        if not obj_dir.exists():
            obj_dir.mkdir(exist_ok=True)
        if not obj_file.exists():
            obj_file.write_bytes(obj.serialize())
        return obj_hash

    def load_index(self) -> Dict[str, str]:
        if not self.index_file.exists():
            return {}
        try:
            return json.loads(self.index_file.read_text())
        except:
            return {}
            
    def save_index(self, index: Dict[str,str]):
         self.index_file.write_text(json.dumps(index,indent=2))       
    def add_file(self, path:str):
        full_path = self.path / path
        if not full_path.exists():
            raise FileNotFoundError(f"Path {path} not found")
        #Read the file content
        content = full_path.read_bytes() #reading the contents of the file

        # Create  BLOB (Binary Large objects) from the content
        blob = Blob(content)
        # store the blob object in database (.bit/objects)
        blob_hash = self.store_objects(blob)
        #Update index to include the file
        index = self.load_index()
        index[path] = blob_hash
        self.save_index(index)
        print(f"Added {path}")
    
    def add_directory(self, path: str):
        full_path = self.path / path
        if not full_path.exists():
            raise FileNotFoundError(f"Directory {path} not found")
        if not full_path.is_dir():
            raise ValueError(f"{path} is not a directory")
        index = self.load_index()
        added_count = 0
        # recursively traverse the directory
        for file_path in full_path.rglob("*"):
            if file_path.is_file(): 
                if ".bit" in file_path.parts or ".git" in file_path.parts:
                    continue
                #create  and store blob objects
                content = file_path.read_bytes()
                blob = Blob(content)
                blob_hash = self.store_objects(blob)
                #update index
                relative_path = str(file_path.relative_to(self.path)) 
                index[relative_path] = blob_hash
                added_count +=1
        self.save_index(index)

        if added_count > 0:
            print(f"Added {added_count} files form directory {path}")
        else:
            print(f"Directory {path} already up to date")
        # create blob objects for all files
        # store all blobs in the object database (.bit/objects)
        #update the indext to include all the files


    def add(self, path:str) -> None:
        full_path = self.path / path
        if not full_path.exists():
            raise FileNotFoundError(f"Path {path} not found")
        if full_path.is_file():
            self.add_file(path)
        elif full_path.is_dir():
            self.add_directory(path)
        else:
            raise ValueError(f"{path} is neither a file not a directory")


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

    #add command
    add_parser = subparsers.add_parser("add", help="Add files and directories to the staging area")
    add_parser.add_argument("paths", nargs="+", help="Files and directories to add")  # "+" means one or more arguments after "add" command
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    repo = Repository()

    try:
        if args.command == "init":
            if not repo.init():
                print("Repository alreaady exists")
                return
        elif args.command == "add":
            if not repo.bit_dir.exists():
                print("Not a bit repository")
                return
            for path in args.paths:
                repo.add(path)



    except Exception as e:
        print(f"Error {e}")
        sys.exit(1)
if __name__ == "__main__":
    main()