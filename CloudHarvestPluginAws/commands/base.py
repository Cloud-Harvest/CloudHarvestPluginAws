from argparse import Namespace
from cmd2 import Cmd2ArgumentParser, CommandSet


def get_subtask(parent: CommandSet, parser: Cmd2ArgumentParser, args: Namespace):
    """
    A routine for selecting the appropriate subtask in a CommandSet to run.
    Args:
        parent: The CommandSet calling this function.
        parser: The command's argument parser.
        args: The parsed arguments.1

    Returns:
        None
    """

    argv = args.cmd2_statement._Cmd2AttributeWrapper__attribute.argv

    try:
        command = argv[1]

    except IndexError:
        parser.print_help()

    else:
        if hasattr(parent, command):
            getattr(parent, command)(args)

        else:
            parser.print_help()
