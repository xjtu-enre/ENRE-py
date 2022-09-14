# type: ignore
import json
import sys
from pathlib import Path
from typing import List

import yaml


def json_entity_dict_to_yaml(ent_obj: dict, is_neg: bool) -> dict:
    yaml_ent_dict = dict()
    yaml_ent_dict["longname"] = ent_obj["longname"]
    yaml_ent_dict["category"] = ent_obj["ent_type"]
    yaml_ent_dict["name"] = ent_obj["name"]
    yaml_ent_dict["loc"] = "{}:{}".format(ent_obj["start_line"],ent_obj["start_col"])
    if is_neg:
        yaml_ent_dict["negative"] = True
    return yaml_ent_dict


def json_entity_list_to_yaml(ent_list: List[dict], is_neg: bool) -> List[dict]:
    ret = []
    for e in ent_list:
        ret.append(json_entity_dict_to_yaml(e, is_neg))
    return ret


def json_entities_to_yaml(entities: List[dict], neg_entities: List[dict]) -> list:
    yaml_entity_obj_list = []
    yaml_entity_obj_list.extend(json_entity_list_to_yaml(entities, False))
    yaml_entity_obj_list.extend(json_entity_list_to_yaml(neg_entities, True))

    return yaml_entity_obj_list
def json_dep_dict_to_yaml(dep_obj: dict, is_neg: bool) -> dict:
    yaml_ent_dict = dict()
    yaml_ent_dict["src"] = dep_obj["src_name"]
    yaml_ent_dict["dest"] = dep_obj["dest_name"]
    yaml_ent_dict["category"] = dep_obj["kind"]
    yaml_ent_dict["loc"] = "{}:{}".format(dep_obj["lineno"],dep_obj["col_offset"])
    if is_neg:
        yaml_ent_dict["negative"] = True
    return yaml_ent_dict

def json_dep_list_to_yaml(deps: List[dict], is_neg: bool) -> list:
    ret = []
    for d in deps:
        ret.append(json_dep_dict_to_yaml(d, is_neg))
    return ret

def json_deps_to_yaml(deps: List[dict], neg_deps: List[dict]) -> list:
    yaml_dep_obj_list = []
    yaml_dep_obj_list.extend(json_dep_list_to_yaml(deps, False))
    yaml_dep_obj_list.extend(json_dep_list_to_yaml(neg_deps, True))
    return yaml_dep_obj_list



def load_json_dep(file_path: Path):
    dep_obj = json.loads(file_path.read_text())
    entities = dep_obj["Entities"]
    dependencies = dep_obj["Dependencies"]
    neg_entities = dep_obj["Negative Entities"]
    neg_dependencies = dep_obj["Negative Dependencies"]
    return entities, dependencies, neg_entities, neg_dependencies


def translate_json(json_dep_file: Path):
    entities, dependencies, neg_entities, neg_dependencies = load_json_dep(json_dep_file)
    yaml_dependencies = json_deps_to_yaml(dependencies, neg_dependencies)
    yaml_entities = json_entities_to_yaml(entities, neg_entities)
    entities_yaml = dict()
    entities_yaml["exact"] = False
    entities_yaml["items"] = yaml_entities
    deps_yaml = dict()
    deps_yaml["exact"] = False
    deps_yaml["items"] = yaml_dependencies

    yaml_entities_repr = dict()
    yaml_entities_repr["name"] = "TBA"
    yaml_entities_repr["entity"] = entities_yaml
    yaml_entities_repr["relation"] = deps_yaml

    test_case_name = json_dep_file.name.removesuffix(".json")
    with open(f"{test_case_name}.yaml", "w") as file:
        yaml.dump(yaml_entities_repr, file)


def entry() -> None:
    test_dir = Path(sys.argv[1])
    for file in test_dir.iterdir():
        if file.name.endswith(".json") and "meta_data" not in file.name:
            translate_json(file)


if __name__ == '__main__':
    entry()
