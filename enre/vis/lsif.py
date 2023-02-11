import sys
sys.path.append('D:/2022/ENRE-py')
import json
import base64
from pathlib import Path
from typing import Literal
from enre.__main__ import enre_wrapper

from enre.analysis.analyze_manager import RootDB
from enre.ent.EntKind import EntKind, RefKind

def to_lsif(package_db: RootDB):

    class startIdCounter:
        def __init__(self) -> None:
            self.base = 0

        def next(self):
            self.base += 1
            return self.base

    counter = startIdCounter()
    result: list[str] = []

    # TODO maybe just use the RootDB.root_dir, this function could be removed
    def toQualifiedWorkspaceRoot(raw: str):
        p = Path(raw)

        if not p.is_absolute:
            #TODO get p's absolute path
            ...

        return 'file:///' + str(p).replace("\\",'/')


    def registerEntry(
        type: Literal['vertex', 'edge'],
        # TODO: need to add other labels here with the support of textDocument/xxx
        label: Literal['metaData', 'source', 'capabilities', '$event', 'project', 'document', 'resultSet', 'range', 
                    'hoverResult', 'definitionResult', 'referenceResult', 'typeDefinitionResult', 'contains', 'item', 'next', 
                    'textDocument/hover', 'textDocument/definition', 'textDocument/references', 'textDocument/typeDefinition'],
        extra: dict
    ) -> dict:
        id = counter.next()
        content = {'id': id, 'type': type, 'label': label, **extra}

        ret = {'id': id, 'content': json.dumps(content)}

        return ret

    
    result.append(registerEntry('vertex', 'metaData', {'version': '0.6.0-next.7', 'positionEncoding': 'utf-16'})['content'])
    result.append(registerEntry('vertex', 'source', {'workspaceRoot': toQualifiedWorkspaceRoot(str(package_db.root_dir))})['content'])
    result.append(registerEntry('vertex', 'capabilities', {'hoverProvider': True, 'declarationProvider': False, 
                                'definitionProvider': True, 'typeDefinitionProvider': True,
                                'referencesProvider': True, 'documentSymbolProvider': True,
                                # Folding range is unsupported by ENRE
                                'foldingRangeProvider': False, 'diagnosticProvider': True})['content'])

    
    idMap:dict = {}

    # visit entity tree
    # package_db.tree contains all the .py files in the root package
    # and package_db.global_db.global_db.ents contains all the package Entities
    for rel_path, module_db in package_db.tree.items():
        # TODO path is incorrect and function's localtion lacks of end
        module_path = module_db.project_root.parent.joinpath(module_db.module_path)
        print(module_path)
        with open(module_path, mode = 'rb') as file:
            # TODO what kind of path should be here? casefold() just for D: -> d:
            fileEntry = registerEntry('vertex', 'document', {'uri': 'file:///' + str(module_path).replace("\\",'/').casefold(), 'languageId': 'python',
            # This could be removed if we no longer use that vscode extension (which requires this to display the document text)
                                    'contents': base64.b64encode(file.read()).decode('utf-8')})

        # idMap: two kinds(1.module: {'id':, 'contains':, 'foldings':} 2. entity:{'id':,'result_set':,'definition':,'references':} )
        # entity's idMap: 'references': [] which contains all the references    'definition':[] which contains the definition's id
        idMap[module_db.module_ent.id] = {'id': fileEntry['id'], 'contains': [], 'foldings': []}
        result.append(fileEntry['content'])

        ranges: list = idMap[module_db.module_ent.id]['contains']
        folding_ranges: list = idMap[module_db.module_ent.id]['foldings']
        
        # same with representation.py write_ent_repr()
        helper_ent_types = [EntKind.ReferencedAttr, EntKind.Anonymous, EntKind.Module]

        # module_db.dep_db.ents contains all the entities in a module
        # TODO module_db.module_ent is in the module_db.dep_db.ents, should it be removed? (yes?)
        for ent in module_db.dep_db.ents:
            # ignore some unresolved attribuite and module kind
            if ent.kind() in helper_ent_types:
                continue
            
            full_range = {'start': {'line': ent.location.code_span.start_line - 1, 'character': ent.location.code_span.start_col},
                            'end': {'line': ent.location.code_span.end_line - 1, 'character': ent.location.code_span.end_col}}
            # add tag and foldingRange(support Class and Func only for now)
            if ent.kind() == EntKind.Class or ent.kind() == EntKind.Function:
                # class:5 func: 12
                kind = 12 if ent.kind() == EntKind.Function else 5
                folding_ranges.append(full_range)
                location = {'start': {'line': ent.location.code_span.start_line - 1, 'character': ent.location.head_col},
                        'end': {'line': ent.location.code_span.start_line - 1, 'character': ent.location.head_col + len(ent.longname.name)},
                        'tag': {'type': "definition", 'text': ent.longname.name, 'kind': kind, 'fullRange': full_range}}
            else:
                location = full_range
            
            entRange = registerEntry('vertex', 'range', location)
            resultSet = registerEntry('vertex', 'resultSet', {})
            nextEdge = registerEntry('edge', 'next', {'outV': entRange['id'], 'inV': resultSet['id']})

            ranges.append(entRange['id'])
            result.append(entRange['content'])
            result.append(resultSet['content'])
            result.append(nextEdge['content'])
            idMap[ent.id] = {'id': entRange['id'], 'result_set': resultSet['id'], 'definition': [entRange['id']], 'references': []}

            # textDocument/hover
            # TODO: cant show builtin function
            entHover = registerEntry('vertex', 'hoverResult',{
                'result': {
                    'contents': [
                        {'language': 'python', 'value': f"{ent.kind()} {ent.longname.name}"},
                        {'language': 'python', 'value': 'Some custom contents...'}
                    ]
                }
            })
            
            result.append(entHover['content'])
            result.append(registerEntry('edge', 'textDocument/hover', {'outV': resultSet['id'], 'inV': entHover['id']})['content'])


    # visit relation
    for rel_path, module_db in package_db.tree.items():
        helper_ent_types = [EntKind.ReferencedAttr, EntKind.Anonymous]
        # this section may put into the section of visiting entity?
        for ent in module_db.dep_db.ents:
            if ent.kind() in helper_ent_types:
                continue
            for ref in ent.refs():
                if ref.target_ent.kind() in helper_ent_types:
                    continue

                location = {'start': {'line': ref.lineno - 1, 'character': ref.col_offset},
                        'end': {'line': ref.lineno - 1, 'character': ref.col_offset + len(ref.target_ent.longname.name)}}
                refRange = registerEntry('vertex', 'range', location)

                result.append(refRange['content'])

                # ent is not package entity, so ref.target_ent.id must have the result_set
                try:
                    resultSet = idMap[ref.target_ent.id]['result_set'] if 'result_set' in idMap[ref.target_ent.id] else None
                except:
                    # TODO some builtin and unknown ent dont have idMap[ref.target_ent.id]
                    # so there will throw error
                    # print("--------error----------------")
                    # print(ref.target_ent.longname.longname, ent.longname.longname)
                    # print(f"{refRange['id']}  kind: {ref.ref_kind.value}, location: {location}")
                    continue
                
                nextEdge = registerEntry('edge', 'next', {'outV': refRange['id'], 'inV': resultSet})
                result.append(nextEdge['content'])

                idMap[module_db.module_ent.id]['contains'].append(refRange['id'])

                # print(f"{refRange['id']}  kind: {ref.ref_kind.value}, location: {location}")

                # process according to the relation kind
                # defination
                if ref.ref_kind == RefKind.UseKind or ref.ref_kind == RefKind.CallKind or ref.ref_kind == RefKind.DefineKind or ref.ref_kind == RefKind.ImportKind or ref.ref_kind == RefKind.SetKind:
                    # add reference to ent's references
                    # enre's entities qualified names are different from each other,
                    # so there is no need to add property: definitions (yes?)
                    references = idMap[ref.target_ent.id]['references'] if 'references' in idMap[ref.target_ent.id] else None
                    references.append(refRange['id'])
                
                # typedefinitaion
                elif ref.ref_kind == RefKind.Annotate:
                    #TODO here should be the entity's result set(should add error handle?)
                    resultSet = idMap[ent.id]['result_set']
                    typeDefinitionResult = registerEntry('vertex', 'typeDefinitionResult', {})
                    typeDefinitionEdge = registerEntry('edge', 'textDocument/typeDefinition', {'outV': resultSet, 'inV': typeDefinitionResult['id']})

                    result.append(typeDefinitionResult['content'])
                    result.append(typeDefinitionEdge['content'])

                    result.append(registerEntry('edge', 'item', {'outV': typeDefinitionResult['id'], 'inVs': idMap[ref.target_ent.id]['definition']})['content'])

                    references = idMap[ref.target_ent.id]['references'] if 'references' in idMap[ref.target_ent.id] else None
                    references.append(refRange['id'])

                elif ref.ref_kind == RefKind.AliasTo:
                    # change the ent's 'definition' to idMap[ref.target_ent.id]['id']
                    idMap[ent.id]['definition'] = [idMap[ref.target_ent.id]['id']]

                elif ref.ref_kind == RefKind.HasambiguousKind:
                    #TODO # change the ent's 'definition' to [] which contains all the definitions
                    ...

                elif ref.ref_kind == RefKind.InheritKind:
                    # there is no need to add add reference to ent's references
                    # because it's added in the ref.ref_kind == RefKind.UseKind
                    # that's the reason why I have to move the 'add references' to the inner of process of Refkind
                    # and with this I dont have to filter the references list to remove repeted locations
                    ...


    # add references to referenceResult('property': 'references', ignore 'definitaions')
    for rel_path, module_db in package_db.tree.items():
        for ent in module_db.dep_db.ents:
            helper_ent_types = [EntKind.ReferencedAttr, EntKind.Anonymous]
            if ent.kind() in helper_ent_types:
                continue
            entry = idMap[ent.id]

            if 'references' in entry and len(entry['references']) > 0:
                resultSet = entry['result_set']
                references = entry['references']
                referenceResult = registerEntry('vertex', 'referenceResult', {})
                referenceEdge = registerEntry('edge', 'textDocument/references', {'outV': resultSet, 'inV': referenceResult['id']})
                itemEdge = registerEntry('edge', 'item', {'outV': referenceResult['id'], 'inVs': references, 'property': 'references'})

                result.append(referenceResult['content'])
                result.append(referenceEdge['content'])
                result.append(itemEdge['content'])

    # add definitionResult
    for rel_path, module_db in package_db.tree.items():
        for ent in module_db.dep_db.ents:
            helper_ent_types = [EntKind.ReferencedAttr, EntKind.Anonymous]
            if ent.kind() in helper_ent_types:
                continue
            entry = idMap[ent.id]

            if 'definition' in entry and len(entry['definition']) > 0:
                resultSet = entry['result_set']
                definitions = entry['definition']
                definitionResult = registerEntry('vertex', 'definitionResult', {})
                definitionEdge = registerEntry('edge', 'textDocument/definition', {'outV': resultSet, 'inV': definitionResult['id']})

                result.append(definitionResult['content'])
                result.append(definitionEdge['content'])

                result.append(registerEntry('edge', 'item', {'outV': definitionResult['id'], 'inVs': definitions})['content'])


    # add contains edge
    for rel_path, module_db in package_db.tree.items():
        fileEntry = idMap[module_db.module_ent.id]
        result.append(registerEntry('edge', 'contains', {'outV': fileEntry['id'], 'inVs': fileEntry['contains']})['content'])
        # add foldingRangeResult
        foldingRangeResult = registerEntry('vertex', 'foldingRangeResult', {'result': fileEntry['foldings']})
        result.append(foldingRangeResult['content'])
        result.append(registerEntry('edge', 'textDocument/foldingRange', {'outV': fileEntry['id'], 'inV': foldingRangeResult['id']})['content'])

    
    return result





if __name__ == '__main__':
    root_path = Path(sys.argv[1])
    
    manager = enre_wrapper(root_path, True, False, False, None)
    
    print("------------------start-----------------------")
    ret = to_lsif(manager.root_db)

    # print(str(ret))

    with open(root_path.absolute().joinpath('output.lsif'), 'w') as file:
        for line in ret:
            file.write(line)
            file.write('\n')
    