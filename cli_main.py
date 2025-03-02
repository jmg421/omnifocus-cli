import sys
import argparse

from commands.add_command import handle_add
from commands.list_command import handle_list
from commands.complete_command import handle_complete
from commands.prioritize_command import handle_prioritize
from commands.delegation_command import handle_delegation

def main():
    parser = argparse.ArgumentParser(
        description="OmniFocus CLI - Manage tasks, projects, and priorities with AI."
    )

    subparsers = parser.add_subparsers(dest="command")

    # Add Command
    add_parser = subparsers.add_parser("add", help="Add a new task or project.")
    add_parser.add_argument("--title", "-t", required=True, help="Title of the new task.")
    add_parser.add_argument("--project", "-p", help="Project to place the task in.")
    add_parser.add_argument("--note", "-n", help="Optional note.")
    add_parser.add_argument("--due", "-d", help="Due date/time (natural language or YYYY-MM-DD).")

    # List Command
    list_parser = subparsers.add_parser("list", help="List tasks or projects.")
    list_parser.add_argument("--project", "-p", help="Filter tasks by project.")
    list_parser.add_argument("--json", action="store_true", help="Output in JSON format.")

    # Complete Command
    complete_parser = subparsers.add_parser("complete", help="Mark tasks complete.")
    complete_parser.add_argument("task_id", nargs="+", help="One or more task IDs to complete.")

    # Prioritize Command
    prioritize_parser = subparsers.add_parser("prioritize", help="Use AI to prioritize tasks.")
    prioritize_parser.add_argument("--project", "-p", help="Project to focus on.")
    prioritize_parser.add_argument("--limit", "-l", type=int, default=10,
                                   help="Number of tasks to include in AI prioritization.")

    # Delegation Command
    delegation_parser = subparsers.add_parser("delegate", help="Delegate tasks to someone else.")
    delegation_parser.add_argument("task_id", help="Task ID to delegate.")
    delegation_parser.add_argument("--to", required=True, help="Email or name of the person.")
    delegation_parser.add_argument("--method", default="email", help="Delegate via email or other method.")

    args = parser.parse_args()

    if args.command == "add":
        handle_add(args)
    elif args.command == "list":
        handle_list(args)
    elif args.command == "complete":
        handle_complete(args)
    elif args.command == "prioritize":
        handle_prioritize(args)
    elif args.command == "delegate":
        handle_delegation(args)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()

