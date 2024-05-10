from cmd2 import Cmd2ArgumentParser
from rich_argparse import RawTextRichHelpFormatter


parser = Cmd2ArgumentParser(formatter_class=RawTextRichHelpFormatter)
subparser = parser.add_subparsers()

# cache collect
credentials_parser = Cmd2ArgumentParser(formatter_class=RawTextRichHelpFormatter)
