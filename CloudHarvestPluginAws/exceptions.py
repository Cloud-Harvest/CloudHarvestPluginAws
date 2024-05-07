from cloud_harvest_core_tasks.exceptions import BaseHarvestException


class HarvestAwsException(BaseHarvestException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class HarvestAwsDataCollectionException(BaseHarvestException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class HarvestAwsTaskException(BaseHarvestException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
