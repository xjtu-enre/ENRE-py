import base64
from typing import Literal

from enre.analysis.analyze_manager import RootDB
from enre.ent.EntKind import EntKind, RefKind
from enre.ent.entity import Span

class startIdCounter:
        def __init__(self) -> None:
            self.base = 0

        def next(self):
            self.base += 1
            return self.base


def to_lsif(package_db: RootDB):

    counter = startIdCounter()
    result: list[str] = []

    # Convenient function to create a LSIF object
    # Return object instead of line-JSON to allow flexible addition.
    def registerEntry(
        type: Literal['vertex', 'edge'],
        # TODO: need to add other labels here with the support of textDocument/xxx
        label: Literal['metaData', 'source', 'capabilities', '$event', 'project', 'document', 'resultSet', 'range', 
                    'hoverResult', 'definitionResult', 'referenceResult', 'typeDefinitionResult', 'contains', 'item', 'next', 
                    'textDocument/hover', 'textDocument/definition', 'textDocument/references', 'textDocument/typeDefinition'
                    'textDocument/foldingRange'],
        extra: dict
    ) -> dict:
        id = counter.next()
        content = {'id': id, 'type': type, 'label': label, **extra}

        return content

    
    result.append(registerEntry('vertex', 'metaData', {'version': '0.6.0-next.7', 'positionEncoding': 'utf-16'}))
    result.append(registerEntry('vertex', 'source', {'workspaceRoot': 'file:///' + str(package_db.root_dir).replace("\\",'/')}))
    result.append(registerEntry('vertex', 'capabilities', {'hoverProvider': True, 'declarationProvider': False, 
                                'definitionProvider': True, 'typeDefinitionProvider': True,
                                'referencesProvider': True, 'documentSymbolProvider': True,
                                'foldingRangeProvider': True, 'diagnosticProvider': True}))

    
    idMap:dict = {}

    
    # package_db.tree contains all the .py files in the root package
    # and package_db.global_db.global_db.ents contains all the package Entities
    for rel_path, module_db in package_db.tree.items():
        # For all module entities, create corresponding document object first.
        module_path = module_db.project_root.parent.joinpath(module_db.module_path)
        
        with open(module_path, mode = 'rb') as file:
            # TODO what kind of path should be here? casefold() just for D: -> d:
            fileEntry = registerEntry('vertex', 'document', {'uri': 'file:///' + str(module_path).replace("\\",'/').casefold(), 'languageId': 'python',
            # This could be removed if we no longer use that vscode extension (which requires this to display the document text)
                                    'contents': base64.b64encode(file.read()).decode('utf-8')})

        # idMap:
        # 1.module: {'id':, 'contains': all the range ids in the module, 'foldings': all the folding ranges in the module} 
        # 2.entity: {'id':, 'result_set':, 'definition': definition range id of this entity, 'references': all the references of the entity}
        idMap[module_db.module_ent.id] = {'id': fileEntry['id'], 'contains': [], 'foldings': []}
        result.append(fileEntry)

        ranges: list = idMap[module_db.module_ent.id]['contains']
        folding_ranges: list = idMap[module_db.module_ent.id]['foldings']
        
        # same with representation.py write_ent_repr()
        helper_ent_types = [EntKind.ReferencedAttr, EntKind.Anonymous, EntKind.Module]

        # Visit entity tree: gather (def) ranges and create corrsponding result set.
        # module_db.dep_db.ents contains all the entities in a module
        # module_db.module_ent is in the module_db.dep_db.ents, so it would be ingored
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
            result.append(entRange)
            result.append(resultSet)
            result.append(nextEdge)
            idMap[ent.id] = {'id': entRange['id'], 'result_set': resultSet['id'], 'definition': [entRange['id']], 'references': []}

            # textDocument/hover
            entHover = registerEntry('vertex', 'hoverResult',{
                'result': {
                    'contents': [
                        {'language': 'python', 'value': f"{ent.kind()} {ent.longname.name}"},
                        {'language': 'python', 'value': 'Some custom contents...'}
                    ]
                }
            })
            
            result.append(entHover)
            result.append(registerEntry('edge', 'textDocument/hover', {'outV': resultSet['id'], 'inV': entHover['id']}))


    # Extract ranges from relations, and save them into idMap (cache).
    # This pass only produce and save LSIF ranges (categoried by usage), not creating any edge.
    for rel_path, module_db in package_db.tree.items():
        # rangeMap: avoid repeated adding range vertex of the same location
        rangeMap: dict = {}
        helper_ent_types = [EntKind.ReferencedAttr, EntKind.Anonymous, EntKind.UnknownVar, EntKind.UnknownModule, EntKind.AmbiguousAttr, EntKind.UnresolvedAttr]
        
        for ent in module_db.dep_db.ents:
            if ent.kind() in helper_ent_types:
                continue
            for ref in ent.refs():
                if ref.target_ent.kind() in helper_ent_types:
                    continue
                
                refRange_span = Span(ref.lineno - 1, ref.col_offset, ref.lineno - 1, ref.col_offset + len(ref.target_ent.longname.name))

                # DefineKind and ContainKind dont need to generate range vertex.
                # Relation: Define
                # just add reference and continue
                if ref.ref_kind == RefKind.DefineKind:
                    references = idMap[ref.target_ent.id]['references'] if 'references' in idMap[ref.target_ent.id] else None
                    references.append(idMap[ref.target_ent.id]['id'])
                    # no need to generate range vertex because it's added above
                    # add it to rangeMap to avoid repeated adding
                    rangeMap[refRange_span] = idMap[ref.target_ent.id]
                    continue
                # Relation: Contain
                # no need to generate range vertex unless we need to add package info
                # just continue
                elif ref.ref_kind == RefKind.ContainKind:
                    continue
                # Relation: Alias
                # change the ent's 'definition' to idMap[ref.target_ent.id]['id']
                # no need to add reference, as it's added in the ralation Define
                # and no need to generate range vertex as it's done in the process of Define(here the location of AliasTo is wrong)
                elif ref.ref_kind == RefKind.AliasTo:
                    idMap[ent.id]['definition'] = [idMap[ref.target_ent.id]['id']]
                    continue

                # Other relations should generate range vertex.
                if refRange_span not in rangeMap:
                    location = {'start': {'line': ref.lineno - 1, 'character': ref.col_offset},
                            'end': {'line': ref.lineno - 1, 'character': ref.col_offset + len(ref.target_ent.longname.name)}}
                    refRange = registerEntry('vertex', 'range', location)

                    result.append(refRange)

                    rangeMap[refRange_span] = refRange

                    # ent is not package entity, so ref.target_ent.id must have the result_set
                    try:
                        resultSet = idMap[ref.target_ent.id]['result_set']
                    except:
                        # TODO some builtin and unknown ent dont have idMap[ref.target_ent.id]
                        # so there will throw error
                        print(ref.target_ent.id)
                        print(ref.target_ent.longname.name)
                        print(ref.target_ent.kind())
                        if ref.target_ent.kind() == EntKind.Module:
                            continue
                    
                    nextEdge = registerEntry('edge', 'next', {'outV': refRange['id'], 'inV': resultSet})
                    result.append(nextEdge)

                    idMap[module_db.module_ent.id]['contains'].append(refRange['id'])
                else:
                    refRange = rangeMap[refRange_span]


                # General relations: Use、Call、Set、Import
                # add reference to ent's references
                if ref.ref_kind == RefKind.UseKind or ref.ref_kind == RefKind.CallKind or ref.ref_kind == RefKind.SetKind or ref.ref_kind == RefKind.ImportKind:
                    references = idMap[ref.target_ent.id]['references'] if 'references' in idMap[ref.target_ent.id] else None
                    if references is None:
                        # TODO: 或许修改为ts那边的区分module的就能够避免这里的问题(这里出错原因是target是module，而module的map里没有这些，只存在于import xx的类型中)
                        # 或者不存在的直接创建reference？
                        print(idMap[ref.target_ent.id])
                        print(ref.ref_kind)
                        print(ref.target_ent.kind())
                        print(ref.target_ent.longname.longname)
                    else:
                        references.append(refRange['id'])

                elif ref.ref_kind == RefKind.ImportKind:
                    # TODO: is import xx and from xx import * should be consider?
                    ...
                
                # Relation: Annotate
                # add typeDefinitionResult vertex
                # add reference to ent's references
                elif ref.ref_kind == RefKind.Annotate:
                    resultSet = idMap[ent.id]['result_set']
                    typeDefinitionResult = registerEntry('vertex', 'typeDefinitionResult', {})
                    typeDefinitionEdge = registerEntry('edge', 'textDocument/typeDefinition', {'outV': resultSet, 'inV': typeDefinitionResult['id']})
                    itemEdge = registerEntry('edge', 'item', {'outV': typeDefinitionResult['id'], 'inVs': idMap[ref.target_ent.id]['definition']})

                    result.append(typeDefinitionResult)
                    result.append(typeDefinitionEdge)
                    result.append(itemEdge)

                elif ref.ref_kind == RefKind.HasambiguousKind:
                    #TODO # change the ent's 'definition' to [] which contains all the definitions
                    ...

                elif ref.ref_kind == RefKind.InheritKind:
                    # there is no need to add reference to ent's references
                    # because it's added in the ref.ref_kind == RefKind.UseKind
                    # that's the reason why I have to move the 'add references' to the inner of process of Refkind
                    # and with this I dont have to filter the references list to remove repeted locations
                    cache = idMap[ref.target_ent.id]
                    if 'implementations' not in cache:
                        cache['implementations'] = []
                    
                    refRange_span = Span(ref.lineno - 1, ref.col_offset, ref.lineno - 1, ref.col_offset + len(ent.longname.name))
                    refRange = rangeMap[refRange_span]
                    cache['implementations'].append(refRange['id'])


    # For module entity, generate document-contains-ranges edge and foldingRangeResult vertex and edge.
    # For other entities, generate referenceResult and definitionResult.
    for rel_path, module_db in package_db.tree.items():
        fileEntry = idMap[module_db.module_ent.id]

        # generate contains edge
        containsEdge = registerEntry('edge', 'contains', {'outV': fileEntry['id'], 'inVs': fileEntry['contains']})
        result.append(containsEdge)

        # generate foldingRangeResult
        foldingRangeResult = registerEntry('vertex', 'foldingRangeResult', {'result': fileEntry['foldings']})
        foldingRangeEdge = registerEntry('edge', 'textDocument/foldingRange', {'outV': fileEntry['id'], 'inV': foldingRangeResult['id']})
        result.append(foldingRangeResult)
        result.append(foldingRangeEdge)

        # generate module range vertex
        location = {'start': {'line': 0, 'character': 0}, 'end': {'line': 0, 'character': 0}}
        entRange = registerEntry('vertex', 'range', location)
        resultSet = registerEntry('vertex', 'resultSet', {})
        nextEdge = registerEntry('edge', 'next', {'outV': entRange['id'], 'inV': resultSet['id']})
        ranges = fileEntry['contains']
        ranges.append(entRange['id'])
        result.append(entRange)
        result.append(resultSet)
        result.append(nextEdge)

        entHover = registerEntry('vertex', 'hoverResult',{
                'result': {
                    'contents': [
                        {'language': 'python', 'value': f"{module_db.module_ent.kind()} {module_db.module_ent.longname.name}"},
                        {'language': 'python', 'value': 'Some custom contents...'}
                    ]
                }
            })
        result.append(entHover)
        result.append(registerEntry('edge', 'textDocument/hover', {'outV': resultSet['id'], 'inV': entHover['id']}))
        fileEntry['result_set'] = resultSet['id']
        fileEntry['references'] = [entRange['id']]
        fileEntry['definition'] = [entRange['id']]

        for ent in module_db.dep_db.ents:
            helper_ent_types = [EntKind.ReferencedAttr, EntKind.Anonymous]
            if ent.kind() in helper_ent_types:
                continue

            cache = idMap[ent.id]

            if 'references' in cache and len(cache['references']) > 0:
                resultSet = cache['result_set']
                references = cache['references']
                referenceResult = registerEntry('vertex', 'referenceResult', {})
                referenceEdge = registerEntry('edge', 'textDocument/references', {'outV': resultSet, 'inV': referenceResult['id']})
                itemEdge = registerEntry('edge', 'item', {'outV': referenceResult['id'], 'inVs': references, 'property': 'references'})

                result.append(referenceResult)
                result.append(referenceEdge)
                result.append(itemEdge)

            if 'definition' in cache and len(cache['definition']) > 0:
                resultSet = cache['result_set']
                definitions = cache['definition']
                definitionResult = registerEntry('vertex', 'definitionResult', {})
                definitionEdge = registerEntry('edge', 'textDocument/definition', {'outV': resultSet, 'inV': definitionResult['id']})
                # cannot add 'property': definitions(the extension will throw error)
                itemEdge = registerEntry('edge', 'item', {'outV': definitionResult['id'], 'inVs': definitions})

                result.append(definitionResult)
                result.append(definitionEdge)
                result.append(itemEdge)
            
            if 'implementations' in cache and len(cache['implementations']) > 0:
                resultSet = cache['result_set']
                implementations = cache['implementations']
                implementationResult = registerEntry('vertex', 'implementationResult', {})
                implementationEdge = registerEntry('edge', 'textDocument/implementation', {'outV': resultSet, 'inV': implementationResult['id']})
                itemEdge = registerEntry('edge', 'item', {'outV': implementationResult['id'], 'inVs': implementations, 'property': 'implementationResults'})

                result.append(implementationResult)
                result.append(implementationEdge)
                result.append(itemEdge)

    
    return result
    