from harvest.base.exceptions import BaseHarvestException, BaseDataCollectionException, BaseTaskException


class HarvestAwsException(BaseHarvestException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class HarvestAwsDataCollectionException(BaseHarvestException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class HarvestAwsTaskException(BaseHarvestException):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
