from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
import time
from typing import Dict, List, Tuple
import zlib

class BitObject:
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
    def deserialize(cls, data:bytes) -> BitObject:
        decompressed = zlib.decompress(data)
        null_idx = decompressed.find(b"\0")
        header = decompressed[:null_idx].decode()
        content = decompressed[null_idx + 1:]

        obj_type, size = header.split(b" ") #split by space

        return cls(obj_type, content)
    
class Blob(BitObject): #just store the content
    def __init__(self, content):
        super().__init__("blob", content)
    def get_content(self) -> bytes:
        return self.content

class Tree(BitObject):
    def __init__(self, entries: List[Tuple[str, str, str]] = None):   #mode = file/folder, filename, hash
        self.entries = entries or []
        content = self.serialize_entries()
        super().__init__("tree", content)
    def serialize_entries(self) -> bytes:
        # <mode> <name>\0<hash>
        content = b""
        for mode, name, obj_hash in sorted(self.entries):
            content += f"{mode} {name}\0".encode()
            content += bytes.fromhex(obj_hash)  #fromhex converts hexadecimal back to bytes (because we use hexdigest earlier)
        return content
    def add_entry(self, mode: str, name: str, obj_hash: str):
        self.entries.append((mode, name, obj_hash))
        self.content = self.serialize_entries() #update the content after adding a new entry, new entry for example means a new file or folder is added to the tree, so we need to update the content of the tree object to reflect the changes in the entries

    @classmethod             #we use class method when we dont want to use any variables/instances of the  class such as self.path etc. we dont care about existing instances and want to use an entirely new instance thats when we use classmethod
    def from_content(cls, content:bytes) -> Tree:    #Deserialization
        tree = cls()
        i=0
        while i < len(content):
            null_idx = content.find(b"\0",i) # "i" is where it should start searching from
            if null_idx == -1:
                break
            mode_name = content[i:null_idx].decode()
            mode, name = mode_name.split(" ",1) #split by space, 1 means split only once
            obj_hash = content[null_idx + 1: null_idx + 21].hex()
            tree.entries.append((mode, name, obj_hash))
            i = null_idx + 21
        return tree
class Commit(BitObject):
    def __init__(
            self, 
            tree_hash: str,
            parent_hashes: List[str],
            author: str,  # who wrote the code
            committer: str,  # who committed the code
            message: str,
            timestamp: int = None
            ):
        self.tree_hash = tree_hash
        self.parent_hashes = parent_hashes
        self.author = author
        self.committer = committer
        self.message = message
        self.timestamp = timestamp or int(time.time())

        content = self._serialize_commit()
        super().__init__("commit", content)
    def _serialize_commit(self):
        lines = [f"tree {self.tree_hash}"]
        for parent in self.parent_hashes:
            lines.append(f"parent {parent}")
        lines.append(f"author {self.author} {self.timestamp} +0000")
        lines.append(f"committer {self.committer} {self.timestamp} +0000")
        lines.append("")
        lines.append(self.message)
        #contcatenate and convert to bytes
        return "\n".join(lines).encode()     # we are doing this fucntion instead of just concatenating string directly is to save time complexity
    
    @classmethod
    def from_content(cls, content: bytes):    #deserialization
        lines = content.decode().split("\n")
        tree_hash = None
        parent_hashes = []
        author = None 
        commiter = None
        message_start = 0
        for i, line in enumerate(lines):
            if line.startswith("tree "): # start after 5 characters
                tree_hash = line[5:] #start after 5th character 'tree '
            elif line.startswith("parent "):
                parent_hashes.append(line[7:])
            elif line.startswith("author "):
                author_parts = line[7:].rsplit(" ", 2)
                author = author_parts[0]
                timestamp = int(author_parts[1])
            elif line.startswith("committer "):
                committer_parts = line[10:].rsplit(" ", 2)
                author = committer_parts[0]
            elif line == "":
                message_start = i+1 #message starts form next line
                break
        message = "\n".join(lines[message_start:])
        commit = cls(tree_hash, parent_hashes, author, commiter, message, timestamp)
        return commit

         
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
    
    def store_objects(self, obj: BitObject) -> str:
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

    def load_object(self, obj_hash: str) -> BitObject:
        obj_dir = self.objects_dir / obj_hash[:2]
        obj_file = obj_dir / obj_hash[2:]

        if not obj_file.exists():
            raise FileExistsError(f"Object {obj_hash} not found")
        return BitObject.deserialize(obj_file.read_bytes())
    def create_tree_from_index(self):
        index = self.load_index()
        if not index:
            tree = Tree()
            return self.store_objects(tree)
        dirs = {}
        files = {}
        for file_path, blob_hash in index.items():  #{"main.py": "20a878c274ab9a62fc0a88d8b56dd422b11e4ab7"}
            parts = file_path.split("/")
            if len(parts) == 1:
                #meaning its a root file
                files[parts[0]] = blob_hash #{"main.py": "20a878c274ab9a62fc0a88d8b56dd422b11e4ab7"}
            else:
                dir_name = parts[0]
                if dir_name not in dirs:
                    dirs[dir_name] = {}
                current = dirs[dir_name]
                for part in parts[1:-1]: # we use -1 becuase we dont want to include that, we only want direcories not the file name
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = blob_hash # { filename : blob_hash}
            def create_tree_recursive(entries_dict: Dict):
                tree = Tree()
                for name, blob_hash in entries_dict.items():
                    if isinstance(blob_hash, str):  #if blob hash type is str, meaning it's a file
                        tree.add_entry("100644", name, blob_hash) # 100644 indicates that it's a file
                    if isinstance(blob_hash, dict): # if blob hash type is dict, meaning it's  a dir
                        subtree_hash = create_tree_recursive(blob_hash)
                        tree.add_entry("40000",name, subtree_hash) # 40000 indicates it's a dir
                    return self.store_objects(tree)
            root_entries = {**files}
            for dir_name, dir_files in dirs.items():
                root_entries[dir_name] = dir_files
            return create_tree_recursive(root_entries)

    def get_current_branch(self) -> str:
        if not self.head_file.exists():
            return "master"
        head_content = self.head_file.read_text().strip()
        if head_content.startswith("ref: refs/heads/"):
            return head_content[16:]
        return "HEAD" #detached HEAD

    def get_branch_commit(self, current_branch: str):
        branch_file = self.heads_dir / current_branch

        if branch_file.exists():
            return branch_file.read_text().strip()
        return None
    def set_branch_commit(self, current_branch: str, commit_hash: str):
        branch_file = self.heads_dir / current_branch
        branch_file.write_text(commit_hash + "\n")
    
    def commit(self, message: str, author:str="Bit user <user@bit.com>"):
        #create a tree object from the index (staging area)
        tree_hash = self.create_tree_from_index()
        current_branch = self.get_current_branch()
        parent_commit = self.get_branch_commit(current_branch)
        parent_hashes = [parent_commit] if parent_commit else []

        index = self.load_index()
        if not index: #check if index is empty/ wiped
            print("nothing to commit, working tree clean")
            return None
        if parent_commit:
            parent_git_commit_obj = self.load_object(parent_commit) # it will contain tree_hash, parent_hash, author, committer etc..
            parent_commit_data = Commit.from_content(parent_git_commit_obj.content) #deserialization
            if tree_hash == parent_commit_data.tree_hash:
                print("nothing to commit, working tree clean")
                return None
        commit = Commit(
            tree_hash = tree_hash,
            parent_hashes= parent_hashes,
            author = author,
            committer= author,
            message = message,
        )
        commit_hash = self.store_objects(commit) # store in /.bit/objects databse
        self.set_branch_commit(current_branch, commit_hash)
        self.save_index({}) # wiped the index (remove the committed files from staging area)
        print(f"Created commit {commit_hash} on branch {current_branch}")
        return commit_hash


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
    
    #commit command
    commit_parser = subparsers.add_parser("commit", help="Create a new commit")
    commit_parser.add_argument("-m", "--message", help="Commit message", required=True)
    commit_parser.add_argument("--author", help="Author name and email")

    
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
        elif args.command == "commit":
            if not repo.bit_dir.exists():
                print("Not a bit repository")
                return
            author = args.author or "Bit user <user@bit.com>"
            repo.commit(args.message, author)



    except Exception as e:
        print(f"Error {e}")
        sys.exit(1)
if __name__ == "__main__":
    main()