from enre.analysis.value_info import InstanceType, ValueInfo, ConstructorType
from enre.overlays.overlays_builtins import OverlaysBuiltins
from enre.overlays.overlays_typing import OverlaysTyping


class OverlaysDispatcher:
    def __init__(self, manager):
        self.dispatcher_map = {}
        self.overlays_typing = OverlaysTyping(manager)
        self.overlays_builtins = OverlaysBuiltins(manager)

    def handle_instance_or_constructor_type(self, value: InstanceType | ConstructorType):
        module_name = value.class_ent.longname.module_name
        method = '_handle_' + module_name
        visitor = getattr(self, method, self._miss_type)
        return visitor(value)

    def _miss_type(self, value: InstanceType):
        return value

    def _handle_typing(self, value: InstanceType):
        return self.overlays_typing.typing(value)

    def _handle_builtins(self, value: InstanceType):
        return self.overlays_builtins.builtins(value)


