from tasks.base import BaseTask


class AwsSamlAuthenticator(BaseTask):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
