from tasks.base import BaseTask


class AwsTask(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)