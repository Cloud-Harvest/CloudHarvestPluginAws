from flask import Blueprint
from CloudHarvestCorePluginManager.decorators import register_instance


@register_instance
class HarvestBlueprint(Blueprint):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

