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

        obj_type, size = header.split(" ") #split by space

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
        committer = None
        timestamp = None
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
                committer = committer_parts[0]
            elif line == "":
                message_start = i+1 #message starts form next line
                break
        message = "\n".join(lines[message_start:])
        commit = cls(tree_hash, parent_hashes, author, committer, message, timestamp)
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
        print(f"Initialized empyt Bit repository in {self.bit_dir}")
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
            raise FileNotFoundError(f"Object {obj_hash} not found")

        return BitObject.deserialize(obj_file.read_bytes())
    def create_tree_from_index(self):
        index = self.load_index()
        if not index:
            tree = Tree()
            return self.store_objects(tree)
        dirs = {}
        files = {}
        for file_path, blob_hash in index.items():  #{"main.py": "20a878c274ab9a62fc0a88d8b56dd422b11e4ab7"}
            parts = Path(file_path).parts
            if len(parts) == 1:
                #meaning its a root file
                files[parts[0]] = blob_hash #{"main.py": "20a878c274ab9a62fc0a88d8b56dd422b11e4ab7"}
            else:
                dir_name = parts[0]
                if dir_name not in dirs:
                    dirs[dir_name] = {}
                current = dirs[dir_name]
                for part in parts[1:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = blob_hash

        def create_tree_recursive(entries_dict: Dict) -> str:
            tree = Tree()
            for name, blob_hash in sorted(entries_dict.items()):
                if isinstance(blob_hash, str):
                    tree.add_entry("100644", name, blob_hash)
                elif isinstance(blob_hash, dict):
                    subtree_hash = create_tree_recursive(blob_hash)
                    tree.add_entry("40000", name, subtree_hash)

            return self.store_objects(tree)

        root_entries = {**files}
        for dir_name, dir_contents in dirs.items():
            root_entries[dir_name] = dir_contents

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
    def get_files_from_tree_recursive(self, tree_hash: str, prefix: str= ""):
        files = set()
        if not tree_hash or tree_hash == "None":
            return files
        try:
            tree_obj = self.load_object(tree_hash)
            tree = Tree.from_content(tree_obj.content)
            # tree = list<tuple<str, str, str>
            for mode, name, obj_hash in tree.entries:
                full_name = f"{prefix}{name}"
                if mode.startswith("100"):
                    files.add(full_name)
                elif mode.startswith("400"):
                    subtree_files = self.get_files_from_tree_recursive(
                        obj_hash, f"{full_name}/"
                    )
                    files.update(subtree_files)
        except Exception as e:
            print(f"Warning could not read tree {tree_hash}: {e}")

        return files


    def checkout(self, branch: str, create_branch: bool):
        #compute files to clear from previous commit
        previous_branch = self.get_current_branch()
        files_to_clear = set()
        previous_commit_hash = None
        try:
            previous_commit_hash = self.get_branch_commit(previous_branch)
            if previous_commit_hash:
                prev_commit_object = self.load_object(previous_commit_hash)
                prev_commit = Commit.from_content(prev_commit_object.content)
                if prev_commit.tree_hash and prev_commit.tree_hash != "None":
                    files_to_clear = self.get_files_from_tree_recursive(prev_commit.tree_hash)
        except Exception:
            files_to_clear = set()
        #created a new branch
        branch_file = self.heads_dir / branch
        if not  branch_file.exists():
            if create_branch:
                if previous_commit_hash:
                    self.set_branch_commit(branch, previous_commit_hash)
                    print(f"Created new branch {branch}")
                else:
                     print("No commites yet, cannot create a branch")
                     return
            else:
                print(f"Branch '{branch}' not found")
                print(f"Use 'python main.py checkout -b {branch} to create and switch branch")
                return
        if not self.restore_working_directory(branch, files_to_clear):
            return

        self.head_file.write_text(f"ref: refs/heads/{branch}\n")
        print(f"Switched to branch {branch}")

    def restore_tree(self, tree_hash: str, path: Path):
        tree_obj = self.load_object(tree_hash)
        tree = Tree.from_content(tree_obj.content)
        # tree = list<tuple<str, str, str>
        for mode, name, obj_hash in tree.entries:
            file_path = path / name
            if mode.startswith("100"):
                blob_obj = self.load_object(obj_hash)
                blob = Blob(blob_obj.content)
                file_path.write_bytes(blob.content)
            elif mode.startswith("400"):
                file_path.mkdir(exist_ok=True)
                self.restore_tree(obj_hash, file_path)
        

    def restore_working_directory(self, branch: str, files_to_clear: set[str]) -> bool:
        target_commit_hash = self.get_branch_commit(branch)
        if not target_commit_hash:
            # No commit on this branch yet: clear index and allow switching
            self.save_index({})
            return True
        #remove files tracked by previous branch
        for rel_path in sorted(files_to_clear):
            file_path = self.path / rel_path
            try:
                if file_path.is_file():
                    file_path.unlink()
                elif file_path.is_dir():
                    if not any(file_path.iterdir()):
                        file_path.rmdir() #remove empty directories
            except Exception:
                pass
        target_commit_obj = self.load_object(target_commit_hash)
        target_commit = Commit.from_content(target_commit_obj.content)
        if target_commit.tree_hash:
            self.restore_tree(target_commit.tree_hash, self.path)
        self.save_index({})
        return True
    
    def branch(self, branch_name,  delete: bool = False):
        #delete
        if delete and branch_name:
            branch_file = self.heads_dir / branch_name
            if branch_file.exists():
                branch_file.unlink()
                print(f"Deleted branch {branch_name}")
            else:
                print(f"Branch {branch_name} not found")
            return
        current_branch = self.get_current_branch()
        if branch_name:
            current_commit = self.get_branch_commit(current_branch)
            if current_commit:
                self.set_branch_commit(branch_name, current_commit)
                print(f"Created branch {branch_name}")
            else:
                print(f"No commits yet, cannot create a new branch")
        else:
            branches = []
            for branch_file in self.heads_dir.iterdir():
                if branch_file.is_file():
                    branches.append(branch_file.name)
            for branch in sorted(branches):
                current_marker = "* " if branch == current_branch else " "
                print(f"{current_marker}{branch}")

    def log(self, max_count: int = 10):
        current_branch = self.get_current_branch()
        commit_hash = self.get_branch_commit(current_branch)

        if not commit_hash:
            print("No commits yet!")
            return
        count = 0
        while commit_hash and count < max_count: #while commit hash is present and count < max_count
            commit_obj = self.load_object(commit_hash)
            commit = Commit.from_content(commit_obj.content)
            print(f"Commit: {commit_hash}")
            print(f"Author: {commit.author}")
            print(f"Date: {time.ctime(commit.timestamp)}")
            print(f"\n    {commit.message}\n")
            commit_hash = commit.parent_hashes[0] if commit.parent_hashes else None
            count+=1

    def build_index_from_tree(self, tree_hash: str, prefix: str=""):
        index = {}
        try:
            tree_obj = self.load_object(tree_hash)
            tree = Tree.from_content(tree_obj.content)
            # tree = list<tuple<str, str, str>
            for mode, name, obj_hash in tree.entries:
                full_name = f"{prefix}{name}"
                if mode.startswith("100"):
                    index[full_name] = obj_hash
                elif mode.startswith("400"):
                    subindex = self.build_index_from_tree(
                        obj_hash, f"{full_name}/"
                    )
                    index.update(subindex)
        except Exception as e:
            print(f"Warning could not read tree {tree_hash}: {e}")

        return index
    def get_all_files(self) -> List[Path]:
        files = []

        for item in self.path.rglob("*"):
            if ".git" in item.parts or ".bit" in item.parts:
                continue
            if item.is_file():
                files.append(item)
        return files
    def status(self):
        # what branch are we on
        current_branch = self.get_current_branch()
        print(f"On branch {current_branch}")
        index = self.load_index()
        current_commit_hash = self.get_branch_commit(current_branch)
        #build index of the latest commit
        last_index_files = {}
        
        if current_commit_hash:
            try:
                commit_obj = self.load_object(current_commit_hash)
                commit = Commit.from_content(commit_obj.content)
                if commit.tree_hash:
                    last_index_files = self.build_index_from_tree(commit.tree_hash)
            except:
                last_index_files = {}
        # All the files present within the working directory
        working_files = {} # file name -> hash
        for item in self.get_all_files():
            rel_path = str(item.relative_to(self.path))
            try:
                content = item.read_bytes()
                blob = Blob(content)
                working_files[rel_path] = blob.hash()
            except Exception:
                continue
        staged_files = []
        unstaged_files = []
        untracked_files = []
        deleted_files = []
        # what files are stages for commit
        for file_path in set(index.keys()) | set(last_index_files.keys()):
            index_hash = index.get(file_path)
            last_index_hash = last_index_files.get(file_path)

            if index_hash and not last_index_hash:
                staged_files.append(("new file", file_path))
            elif index_hash and index_hash != last_index_hash:
                staged_files.append(("modified", file_path))
        if staged_files:
            print("\nChanges to be committed")
            for stage_status, file_path in sorted(staged_files):
                print(f"   {stage_status}: {file_path}")

        #what files have modified but not staged
        for file_path, working_hash in working_files.items():

            if file_path in index:
                # compare against staged version
                if working_hash != index[file_path]:
                    unstaged_files.append(file_path)

            elif file_path in last_index_files:
                # compare against latest commit
                if working_hash != last_index_files[file_path]:
                    unstaged_files.append(file_path)
        if unstaged_files:
            print("\nChanges not staged for commit:")
            for file_path in sorted(unstaged_files):
                print(f"   modified : {file_path}")

        # what files are untracked
        for file_path in working_files:
            if file_path not in index and file_path not in last_index_files:
                untracked_files.append(file_path)
        if untracked_files:
            print("\nUntracked files:")
            for file_path in sorted(untracked_files):
                print(f"   {file_path}")
        # what files have been deleted
        for file_path in set(index.keys()) | set(last_index_files.keys()):
            if file_path not in working_files:
                deleted_files.append(file_path)
        if deleted_files:
            print("\nDeleted files:")
            for file_path in sorted(deleted_files):
                print(f"  deleted: {file_path}")
        if not staged_files and not unstaged_files and not deleted_files and not untracked_files:
            print("Nothing to commit, working tree clean ")
            
        

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

    #checkout command
    checkout_parser = subparsers.add_parser("checkout", help="Move/Create a new branch")
    checkout_parser.add_argument("branch", help="Branch to switch to")
    checkout_parser.add_argument("-b", "--create-branch", action="store_true",help="Create and switch to a new branch") #creates a boolean value
    # Branch command
    branch_parser = subparsers.add_parser("branch", help="List or manage branches")
    branch_parser.add_argument(
        "name",
        nargs='?'
    )
    branch_parser.add_argument("-d", "--delete", action="store_true", help="Delete the branch")

    # log command
    log_parser = subparsers.add_parser("log", help="Show commit history")
    log_parser.add_argument("-n", "--max-count", type=int, default=10, help="Limit commits displayed")

    #status command
    status_parser = subparsers.add_parser("status", help="show repository status")
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
        elif args.command == "checkout":
            if not repo.bit_dir.exists():
                print("Not a bit repository")
                return
            repo.checkout(args.branch, args.create_branch)
        elif args.command == "branch":
            if not repo.bit_dir.exists():
                print("Not a bit repository")
                return
            repo.branch(args.name, args.delete)
        elif args.command == "log":
            if not repo.bit_dir.exists():
                print("Not a bit repository")
                return
            repo.log(args.max_count)
        elif args.command == "status":
            if not repo.bit_dir.exists():
                print("Not a bit repository")
                return
            repo.status()

    except Exception as e:
        print(f"Error {e}")
        sys.exit(1)
if __name__ == "__main__":
    main()