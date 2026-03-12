"""
Script to perform a Git commit workflow (add + commit + push) and update the
status of a ClickUp task.

Usage:
    python clickup_commit.py --task-id <TASK_ID> --status <STATUS> --message <COMMIT_MESSAGE> --branch <BRANCH>

Example:
    python clickup_commit.py --task-id abc123 --status "in review" --message "feat: add login page" --branch main
"""

import argparse
import os
import subprocess
import sys
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

CLICKUP_API_TOKEN = os.getenv("CLICKUP_API_TOKEN", "")
CLICKUP_BASE_URL = os.getenv("CLICKUP_BASE_URL", "")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


def get_task(task_id: str) -> dict:
    url = f"{CLICKUP_BASE_URL}/task/{task_id}"
    headers = {"Authorization": CLICKUP_API_TOKEN, "Content-Type": "application/json"}

    response = requests.get(url, headers=headers)

    if response.status_code == 404:
        logger.error("ClickUp task '%s' not found.", task_id)
        sys.exit(1)

    if response.status_code != 200:
        logger.error("ClickUp API error (%s): %s", response.status_code, response.text)
        sys.exit(1)

    return response.json()


def get_list_statuses(list_id: str) -> list[str]:
    url = f"{CLICKUP_BASE_URL}/list/{list_id}"
    headers = {"Authorization": CLICKUP_API_TOKEN, "Content-Type": "application/json"}

    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        logger.error("Failed to fetch list statuses (%s): %s", response.status_code, response.text)
        sys.exit(1)

    statuses = response.json().get("statuses", [])
    return [s["status"].lower() for s in statuses]


def validate_status(task: dict, new_status: str) -> None:
    list_id = task.get("list", {}).get("id")

    if not list_id:
        logger.warning("Could not retrieve list ID from task. Skipping status validation.")
        return

    available_statuses = get_list_statuses(list_id)

    if new_status.lower() not in available_statuses:
        logger.error(
            "Status '%s' does not exist in this list. Available statuses: %s",
            new_status,
            ", ".join(available_statuses),
        )
        sys.exit(1)

    logger.info("Status '%s' validated successfully.", new_status)


def update_task_status(task_id: str, new_status: str) -> dict:
    url = f"{CLICKUP_BASE_URL}/task/{task_id}"
    headers = {"Authorization": CLICKUP_API_TOKEN, "Content-Type": "application/json"}

    response = requests.put(url, json={"status": new_status}, headers=headers)

    if response.status_code not in (200, 201):
        logger.error(
            "Failed to update ClickUp task status (%s): %s",
            response.status_code,
            response.text,
        )
        sys.exit(1)

    return response.json()


def run_git(args: list) -> subprocess.CompletedProcess:
    return subprocess.run(["git"] + args, capture_output=True, text=True)


def git_add_all():
    result = run_git(["add", "-A"])

    if result.returncode != 0:
        logger.error("git add failed: %s", result.stderr)
        sys.exit(1)

    logger.info("Git add completed successfully.")


def git_commit(message: str):
    result = run_git(["commit", "-m", message])

    if result.returncode != 0:
        if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
            logger.info("Nothing to commit (working tree clean).")
            sys.exit(0)

        logger.error("git commit failed: %s", result.stderr)
        sys.exit(1)

    logger.info("Commit created: %s", message)

    hash_result = run_git(["rev-parse", "--short", "HEAD"])
    if hash_result.returncode == 0:
        logger.info("Commit hash: %s", hash_result.stdout.strip())


def git_current_branch() -> str:
    result = run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    if result.returncode != 0:
        logger.error("Failed to get current branch: %s", result.stderr)
        sys.exit(1)
    return result.stdout.strip()


def remote_branch_exists(branch: str) -> bool:
    """Check if a branch exists on the remote."""
    result = run_git(["ls-remote", "--heads", "origin", branch])
    return bool(result.stdout.strip())


def resolve_branch(branch_arg: str | None) -> str:
    """
    Resolve the target branch:
    - If --branch was provided, use it directly.
    - Otherwise, detect the current local branch.
    - If the resolved branch does not exist on remote, ask the user
      whether to create it or provide a different branch name.
    """
    if branch_arg:
        branch = branch_arg
    else:
        branch = git_current_branch()
        logger.info("No branch specified. Using current branch: '%s'.", branch)

    # Check remote existence
    if not remote_branch_exists(branch):
        logger.warning("Branch '%s' does not exist on remote.", branch)

        while True:
            print(f"\n  Branch '{branch}' was not found on remote.")
            print("  [1] Create it on remote")
            print("  [2] Enter a different branch name")
            print("  [3] Abort")
            choice = input("  Your choice [1/2/3]: ").strip()

            if choice == "1":
                logger.info("Branch '%s' will be created on remote during push.", branch)
                break
            elif choice == "2":
                new_branch = input("  Enter branch name: ").strip()
                if not new_branch:
                    logger.warning("Branch name cannot be empty. Please try again.")
                    continue
                branch = new_branch
                if remote_branch_exists(branch):
                    logger.info("Branch '%s' found on remote.", branch)
                    break
                else:
                    logger.warning("Branch '%s' also does not exist on remote.", branch)
                    # Loop again with the new branch name
            elif choice == "3":
                logger.info("Aborted by user.")
                sys.exit(0)
            else:
                logger.warning("Invalid choice. Please enter 1, 2, or 3.")

    return branch


def git_push(branch: str):
    """Push commits to the remote branch, creating it if necessary."""
    if remote_branch_exists(branch):
        result = run_git(["push", "origin", branch])
    else:
        result = run_git(["push", "--set-upstream", "origin", branch])

    if result.returncode != 0:
        logger.error("git push failed: %s", result.stderr.strip())
        sys.exit(1)

    logger.info("Git push completed successfully to branch '%s'.", branch)


def main():
    parser = argparse.ArgumentParser(
        description="Perform git add + commit + push and update a ClickUp task status."
    )

    parser.add_argument("--task-id", "-t", required=True, help="ClickUp task ID.")
    parser.add_argument("--status", "-s", required=True, help="New ClickUp task status.")
    parser.add_argument("--message", "-m", required=True, help="Git commit message.")
    parser.add_argument(
        "--branch",
        "-b",
        required=False,
        default=None,
        help="Remote branch to push to (default: current branch).",
    )

    args = parser.parse_args()

    if not CLICKUP_API_TOKEN:
        logger.error("Missing ClickUp API token. Define CLICKUP_API_TOKEN in your .env file.")
        sys.exit(1)

    if not CLICKUP_BASE_URL:
        logger.error("Missing ClickUp API URL. Define CLICKUP_BASE_URL in your .env file.")
        sys.exit(1)

    # Resolve branch (handles missing remote + user interaction)
    branch = resolve_branch(args.branch)
    logger.info("Target branch: %s", branch)

    # Fetch ClickUp task
    logger.info("Fetching ClickUp task '%s'...", args.task_id)
    task = get_task(args.task_id)
    task_name = task.get("name", "Untitled")
    current_status = task.get("status", {}).get("status", "unknown")
    logger.info("Task name: %s", task_name)
    logger.info("Current status: %s", current_status)

    # Validate status before doing anything
    logger.info("Validating status '%s'...", args.status)
    validate_status(task, args.status)

    # Git operations
    logger.info("Starting Git workflow (add + commit + push).")
    git_add_all()
    git_commit(args.message)
    git_push(branch)

    # ClickUp update
    logger.info("Updating ClickUp task status to '%s'...", args.status)
    updated_task = update_task_status(args.task_id, args.status)
    new_status = updated_task.get("status", {}).get("status", args.status)
    logger.info("Status updated: '%s' → '%s'", current_status, new_status)

    task_url = updated_task.get("url", "")
    if task_url:
        logger.info("Task URL: %s", task_url)

    logger.info("Workflow completed successfully.")


if __name__ == "__main__":
    main()
