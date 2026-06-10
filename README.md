# Bit - A Git-inspired version control system

Bit is a **lightweight Git-inspired Version Control System built from scratch in Python**. It implements the fundamental concepts behind modern version control systems, including content-addressable storage, staging, commits, branches, checkout, and repository status tracking.

The primary goal of Bit is to explore and understand how Git works internally by recreating its core architecture without relying on external libraries.

---

## Core Components

### 1. BitObject

The foundation of Bit's object database.

* Base class for Blob, Tree, and Commit objects
* Handles serialization and deserialization
* Compresses data using `zlib`
* Generates SHA-1 hashes for object identification
* Provides content-addressable storage

### 2. Blob Objects

Represent file contents.

* Store raw file data
* Created whenever files are added to the repository
* Immutable once stored

### 3. Tree Objects

Represent directory structures.

* Store references to blobs and subtrees
* Maintain file hierarchy and names
* Create complete repository snapshots

### 4. Commit Objects

Represent repository history.

* Store commit metadata
* Reference tree snapshots
* Track parent commits
* Form the commit history chain

### 5. Repository Class

Manages the entire repository lifecycle.

Responsibilities include:

* Repository initialization
* Object storage and retrieval
* Staging area management
* Commit creation
* Branch management
* Checkout operations
* Status tracking
* Working directory restoration

---

## Features

### Repository Management

* Initialize repositories using `bit init`
* Automatic creation of repository structure
* Branch and reference management

### Object Database

Bit stores data as immutable objects:

| Object Type | Purpose                                  |
| ----------- | ---------------------------------------- |
| Blob        | Stores file contents                     |
| Tree        | Stores directory structures              |
| Commit      | Stores repository snapshots and metadata |

### Content Addressable Storage

* SHA-1 based object identification
* Objects are stored based on content rather than filenames
* Duplicate content automatically reuses existing objects
* Efficient object compression using `zlib`

### Staging Area

* Add individual files
* Add multiple files at once
* Recursively add entire directories
* Maintains an index before commits

### Commit System

* Snapshot-based commits
* Commit messages
* Author metadata
* Parent commit tracking
* Commit history traversal

### Branch Management

* Create branches
* Switch between branches
* Delete branches
* Branch references stored independently

### Repository Status

Detects:

* Staged files
* Modified files
* Untracked files
* Deleted files

### Checkout Support

* Restore working directory from commits
* Switch between branches
* Reconstruct file trees from stored objects

---

## Installation & Setup

### Prerequisites

* Python 3.10+
* No third-party dependencies required

### Clone the Repository

```bash
git clone <repository-url>
cd bit
```

---

## Usage Examples

### Initialize a Repository

```bash
python main.py init
```

Output:

```text
Initialized empty Bit repository
```

---

### Add Files to Staging

Add a single file:

```bash
python main.py add main.py
```

Add multiple files:

```bash
python main.py add file1.py file2.py
```

Add an entire directory:

```bash
python main.py add src/
```

---

### Create a Commit

```bash
python main.py commit -m "Initial commit"
```

Custom author:

```bash
python main.py commit -m "Added feature" --author "Muhammed Sabith <sabith@example.com>"
```

---

### Check Repository Status

```bash
python main.py status
```

Displays:

* Changes to be committed
* Modified files
* Untracked files
* Deleted files

---

### View Commit History

```bash
python main.py log
```

Show only the latest 5 commits:

```bash
python main.py log -n 5
```

---

### Branch Operations

List branches:

```bash
python main.py branch
```

Create a branch:

```bash
python main.py branch feature-x
```

Delete a branch:

```bash
python main.py branch feature-x -d
```

---

### Checkout Branches

Switch to an existing branch:

```bash
python main.py checkout feature-x
```

Create and switch to a new branch:

```bash
python main.py checkout feature-y -b
```

---

## Project Structure

```text
bit/
├── main.py
├── README.md
└── .bit/
    ├── objects/
    │   ├── aa/
    │   ├── bb/
    │   └── ...
    │
    ├── refs/
    │   └── heads/
    │       ├── master
    │       ├── feature-x
    │       └── ...
    │
    ├── HEAD
    └── index
```

---

## How Bit Works

### Object Storage

Each object is stored in the following format:

```text
<type> <size>\0<content>
```

Example:

```text
blob 12\0Hello World!
```

The object is then:

1. Hashed using SHA-1
2. Compressed using zlib
3. Stored in `.bit/objects`

Directory layout:

```text
.bit/objects/e6/8ff7...
```

This follows the same content-addressable storage concept used by Git.

---

### Staging Process

* Files are converted into Blob objects
* Blob hashes are stored in the index
* The index acts as the staging area

---

### Commit Process

* A Tree object is generated from the staged files
* A Commit object references the tree
* Parent commit information is stored
* The current branch is updated to point to the new commit

---

### Branch Management

* Branches are simple references to commit hashes
* New branches inherit the current commit reference
* Checkout restores files from the target branch
* HEAD tracks the active branch

---

## Example Workflow

```bash
python main.py init

python main.py add main.py

python main.py commit -m "Initial commit"

python main.py branch feature

python main.py checkout feature

python main.py add app.py

python main.py commit -m "Add app.py"

python main.py log
```

---

## Current Limitations

Bit currently focuses on the core concepts of version control.

Not yet implemented:

* Merge
* Rebase
* Diff
* Tags
* Remote Repositories
* Push / Pull
* Clone
* Conflict Resolution
* Pack Files
* Garbage Collection
* Ignore Files (.bitignore)

---

## Future Improvements

### Version 2

* Diff Engine
* File Restore
* Improved Status Output

### Version 3

* Three-Way Merge
* Conflict Detection
* Merge Command

### Version 4

* Remote Repositories
* Push/Pull Support
* Clone Functionality

### Version 5

* Pack Files
* Object Optimization
* Performance Improvements

---

## Inspiration

Bit is heavily inspired by Git's internal architecture while remaining intentionally simplified for educational and learning purposes.

The project aims to answer a simple question:

> "What actually happens when we run git add, git commit, and git checkout?"

---

## License

MIT License

---

## Author

**Muhammed Sabith**

Built from scratch in Python to explore the internals of modern version control systems.
