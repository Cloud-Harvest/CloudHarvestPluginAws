from cmd2 import with_default_category, CommandSet, with_argparser, as_subcommand_to
from CloudHarvestPluginAws.commands.aws.arguments import parser, credentials_parser


@with_default_category('Harvest')
class AwsCommand(CommandSet):
    @with_argparser(parser)
    def do_aws(self, args):
        from CloudHarvestPluginAws.commands.base import get_subtask
        get_subtask(parent=self, parser=parser, args=args)

    @as_subcommand_to('cache', 'attach', credentials_parser, help='Retrieve and provision AWS credentials.')
    def credentials(self, args):
        pass
