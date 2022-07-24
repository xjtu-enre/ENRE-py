from typing import Sequence

from enre.cfg.module_tree import ModuleSummary


def from_summaries(summaries: Sequence[ModuleSummary]) -> str:
    ret = ""
    for summary in summaries:
        ret += f"{str(summary)}\n"
        for name, objs in summary.get_namespace().items():
            ret += f"\t{name}: {objs}\n"


    return ret
