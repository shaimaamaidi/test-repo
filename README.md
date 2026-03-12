# TaskGenerator

Automates commit workflows and updates task status in ClickUp using TASK ID.

## Requirements

- Python 3.10+
- See requirements.txt

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

   pip install -r requirements.txt

## Usage

- Create a .env file with the required variables.
- Run the script from the project root.

### Script parameters

The script accepts the following parameters (short and long forms are equivalent):

- `-t` / `--task-id`: ClickUp task ID (example: `-t abc123`).
- `-s` / `--status`: New ClickUp status to set (example: `-s "in review"`).
- `-m` / `--message`: Git commit message (example: `-m "feat: add login page"`).
- `-b` / `--branch`: Remote branch to push to. Optional; defaults to the current Git branch (example: `-b main`).

Example:

   python src/clickup_commit_script.py -t abc123 -s "in review" -m "feat: add login page" -b main

## Branch handling cases

The branch parameter is optional. The cases below apply when running the command with or without specifying a branch.

- Case 1 (with or without specifying branch): if the branch exists on the remote:

- Push normally with `git push origin <branch>`.

- Case 2 (with or without specifying branch): if the branch does not exist on the remote:

- Menu: [1] Create / [2] Abort.

- Case 3 (without specifying branch): if `first_commit` is selected:

- Menu: [1] Create / [2] Abort, and the branch to be created is `main`.

## Examples (screenshots)

![Validate script](docs/images/validate_script.png)
![Push with creating branch](docs/images/push_with_creating_branch.png)
![First push without specifying branch](docs/images/first_push_without_specifying_branch.png)
![Error status](docs/images/error_status.png)

