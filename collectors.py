from base.tasks import Task
from logging import getLogger

logger = getLogger('harvest')


class AwsApiCollector(Task):
    def __init__(self):
        super().__init__()

    def run(self):
        pass
