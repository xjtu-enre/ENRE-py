# E: Module-$ti=test_inherit@

class Base:
    # E: Class-$Base=test_inherit.Base@Base
    # D: Define-$ti->$Base@Base
    static_attr = 1
    # E: Class Attribute-$static_attr=test_inherit.Base.static_attr@static_attr
    # D: $Base->$static_attr@static_attr
    def __init__(self):
        # E: Function-$B_init=test_inherit.Base.__init__@__init__
        # E: Parameter-$B_init_self=test_inherit.Base.__init__.self@self
        # D: Define-$B_init->$B_init_self@self
        self.base_attribute = 1
        # E: Class Attribute-$B_base_attr=test_inherit.Base.base_attribute@base_attribute
        # D: Define-$B_init->$B_init_self@self

class Inherit(Base):
    # E: Class-$Inherit=test_inherit.Inherit@Inherit
    # D: Define-$Inherit->$Base@Base
    # D: Inherit-$Inherit->$Base
    def __init__(self):
        # E: Function-$I_init=test_inherit.Inherit.__init__@__init__
        # E: Parameter-$I_init_self=test_inherit.Inherit.__init__.self@self

        super().__init__()

    def use_attribute(self):
        # E: Function-$I_method=test_inherit.Inherit.use_attribute@use_attr
        print(self.base_attribute)
        # D: Use-$I_method->$B_base_attr@base_attribute

        print(self.static_attr)
        # D: Use-$I_method->$static_attr@static_attr


