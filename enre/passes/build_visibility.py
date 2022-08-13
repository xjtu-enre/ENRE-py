# -*- coding:utf-8
import re

from enre.analysis.analyze_manager import RootDB
from enre.analysis.analyze_method import AbstractClassInfo, FunctionKind
from enre.ent.EntKind import RefKind
from enre.ent.entity import Class, Function, ClassAttribute


class BuildVisibility:
    def __init__(self, package_db: RootDB):
        self._package_db = package_db

    def work_flow(self) -> None:
        for _, module_db in self._package_db.tree.items():
            for ent in module_db.dep_db.ents:
                if isinstance(ent, Class):
                    # 私有变量正则匹配式
                    private_attr_regular = re.compile("^_[A-Za-z0-9]+$")
                    abstract_info: AbstractClassInfo = AbstractClassInfo()
                    flag = False
                    for name, ents in ent.names.items():
                        for entity in ents:
                            if isinstance(entity, Function):
                                if entity.abstract_kind:
                                    # handle abstract_method
                                    abstract_info.abstract_methods.append(entity)
                                    flag = True
                                elif entity.readonly_property_name:
                                    # handle readonly property
                                    if entity.readonly_property_name in ent.names:
                                        for attr_ent in ent.get_attribute(entity.readonly_property_name):
                                            if isinstance(attr_ent, Function):
                                                ent.readonly_attribute[entity.readonly_property_name].append(
                                                    attr_ent)
                            elif isinstance(entity, ClassAttribute) and private_attr_regular.match(name):
                                # handle private attribute
                                ent.private_attribute[name].append(entity)

                    # todo: 目前对于内部类的继承通过_refs分析，完成之后注释掉这个for，取消注释下面for循环的第一个if
                    for ref in ent._refs:
                        if ref.ref_kind == RefKind.InheritKind:
                            if ref.target_ent.longname.name == 'ABC':
                                abstract_info.inherit = "ABC"
                                flag = True

                    for parent_class in ent.inherits:
                        # if parent_class.longname.name == 'ABC':
                        #     # 分析是否直接继承ABC类
                        #     abstract_info.inherit = "ABC"
                        #     flag = True
                        if parent_class.abstract_info:
                            # 分析是否包含抽象类方法，以及是否完全实现了父类的抽象方法
                            for abstract_method in parent_class.abstract_info.abstract_methods:
                                if abstract_method.abstract_kind == FunctionKind.AbstractMethod:
                                    # 不分析构造函数，只分析普通函数
                                    if not ent.implement_method(abstract_method.longname):
                                        abstract_info.abstract_methods.append(abstract_method)
                                        flag = True

                    ent.abstract_info = abstract_info if flag else None
