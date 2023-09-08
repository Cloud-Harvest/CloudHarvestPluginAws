from base.tasks import BaseTask
from logging import getLogger

logger = getLogger('harvest')


class AwsApiCollector(BaseTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run(self):
        pass
