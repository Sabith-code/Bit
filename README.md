# Bit

A simplified Git-like version control system built in Python. Bit implements core VCS concepts including object storage, staging, commits, branching, and checkout — using the same content-addressable storage model as Git.

## Features

- `init` — Initialize a new repository
- `add` — Stage files and directories
- `commit` — Create commits with tree snapshots
- `branch` — Create, list, and delete branches
- `checkout` — Switch branches and restore working directory
- `log` — View commit history
- `status` — Show staged, unstaged, untracked, and deleted files

## How It Works

Bit uses a `.bit/` directory to store all repository data:

```
.bit/
  HEAD          # points to the current branch
  index         # staging area (JSON)
  objects/      # content-addressable object store
  refs/heads/   # branch pointers
```

Three object types are stored, each compressed with zlib and addressed by SHA-1 hash:

- **Blob** — raw file content
- **Tree** — directory snapshot (list of mode/name/hash entries)
- **Commit** — tree hash, parent(s), author, timestamp, and message

## Usage

```bash
# Initialize a repository
python main.py init

# Stage files
python main.py add main.py
python main.py add src/

# Commit
python main.py commit -m "Initial commit"
python main.py commit -m "Fix bug" --author "Alice <alice@example.com>"

# Branches
python main.py branch                  # list branches
python main.py branch feature-x        # create branch
python main.py branch -d feature-x     # delete branch

# Switch branches
python main.py checkout main
python main.py checkout -b new-feature  # create and switch

# History and status
python main.py log
python main.py log -n 5
python main.py status
```

## Requirements

- Python 3.8+
- No external dependencies (uses only the standard library)
