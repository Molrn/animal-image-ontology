import synset_mapper as sm
import Tools.list_dict_tools as LDtools
import Tools.sparql_tools as SPtools
from tqdm import tqdm
import pandas as pd
import json
import os

def get_animal_mapping(animal_mapping_file_path:str='Data/animal_synsets.json')->list[dict]:
    """Get the animal mapping from its file. If the file doesn't exist, generate it

    Args:
        animal_mapping_file_path (str, optional): Path of the file containing the animal mapping. Defaults to 'Data/animal_synsets.json'.

    Returns:
        list[dict]: List of dict containig the mapping of each animal synset
    """
    if not os.path.exists(animal_mapping_file_path):
        synsets = sm.get_synset_full_mapping()
        animal_mapping = [s for s in synsets if s['is_animal']]
        for syn in animal_mapping:
            syn.pop('is_animal')
        animal_file = open(animal_mapping_file_path, 'w')
        json.dump(animal_mapping, animal_file)
        animal_file.close()
        return animal_file
    animal_file = open(animal_mapping_file_path)
    animal_mapping = json.load(animal_file)
    animal_file.close()
    return animal_mapping    

def set_all_synsets_animal_status(mapping_file_path:str='Data/synset_mapping.json', inid_start:str=None):
    """Manually set the WikiData IDs of the synsets who don't have one

    Args:
        mapping_file_path (str, optional): Path of the file containing the synsets. 
            When the function generates an error, the computed synsets are stored in that file. 
            Defaults to 'Data/synset_mapping.json'.
        inid_start (str, optional): ImageNet ID of the synsets to start from. Defaults to None.
    """
    synsets = sm.get_synset_full_mapping(mapping_file_path)
    start_index = 0
    if inid_start:
        start_index = next((i for i, s in enumerate(synsets) if s['inid']==inid_start), 0)
    synsets = LDtools.apply_to_all_dicts(
        synsets,
        is_animal,
        ['wdid'],
        'is_animal',
        mapping_file_path,
        start_index)

    file = open(mapping_file_path, 'w')
    json.dump(synsets, file)
    file.close()

def is_animal(wdid:str)->bool:
    """Check if a WikiData object is an Animal or not

    Args:
        wdid (str): id of the object to check

    Returns:
        bool: True if the object is an animal, Fasle otherwise, None if no id is given
    """
    if not wdid:
        return None
    patterns = get_animal_patterns(wdid)
    query = 'ASK WHERE { {'+'}UNION{'.join([patterns[key] for key in patterns])+'} }'
    return SPtools.ask_query(query)

def get_animal_patterns(wdid:str, pattern_file_path:str='Data/animal_patterns.json')->dict:
    """Get all the animal patterns formatted for a specific WikiData object

    Args:
        wdid (str): ID of the object to format into the patterns
        pattern_file_path (str, optional): Path of the patterns file. Defaults to 'Data/animal_patterns.json'.

    Returns:
        dict: Formatted patterns in a dict. Each patter has format (pattern name: SPARQL pattern description)
    """
    pat_file = open(pattern_file_path)    
    animal_patterns = json.load(pat_file)
    pat_file.close()
    init_patterns = {}
    for key in animal_patterns:
        init_patterns[key] = 'wd:'+wdid+' '+animal_patterns[key]
    return init_patterns

def set_all_animal_pattern(mapping_file_path:str='Data/animal_synsets.json', wdid_start:str=None):
    """Set the pattern of each WikiData object from itself to the Animal class

    Args:
        mapping_file_path (str, optional): Path of the file containing the synsets. 
            When the function generates an error, the computed synsets are stored in that file. 
            Defaults to 'Data/synset_mapping.json'.
        wdid_start (str, optional): WordNet ID of the synsets to start from. Defaults to None.
    """
    synsets = sm.get_synset_full_mapping(mapping_file_path)
    start_index = 0
    if wdid_start:
        start_index = next((i for i, s in enumerate(synsets) if s['wdid']==wdid_start), 0)
    synsets = LDtools.apply_to_all_dicts(
        synsets,
        get_object_pattern,
        ['wdid'],
        'animal_pattern',
        mapping_file_path,
        start_index)
    file = open(mapping_file_path, 'w')
    json.dump(synsets, file)
    file.close()

def get_object_pattern(wdid:str)->str:
    """Get the pattern to the animal class of a WikiData object

    Args:
        wdid (str): ID of the WikiData object

    Returns:
        str: name of the pattern
    """
    if not wdid:
        return None
    patterns = get_animal_patterns(wdid)
    for pat_name, pat in patterns.items():
        if SPtools.ask_query('ASK WHERE { '+pat+' }') :
            return pat_name
    return None

def set_all_animal_path_mapping(mapping_file_path:str='Data/animal_synsets.json', wdid_start:str=None):
    """Set the path mapping of each WikiData object from itself to the Animal class.

    Args:
        mapping_file_path (str, optional): Path of the file containing the synsets. 
            When the function generates an error, the computed synsets are stored in that file. 
            Defaults to 'Data/synset_mapping.json'.
        wdid_start (str, optional): WordNet ID of the synsets to start from. Defaults to None.
    """
    synsets = sm.get_synset_full_mapping(mapping_file_path)
    start_index = 0
    if wdid_start:
        start_index = next((i for i, s in enumerate(synsets) if s['wdid']==wdid_start), 0)
    synsets = LDtools.apply_to_all_dicts(
        dict_list=synsets,
        function=animal_path_mapping,
        arg_keys=['wdid', 'animal_pattern'], 
        error_save_path=mapping_file_path,
        start_index=start_index)
    file = open(mapping_file_path, 'w')
    json.dump(synsets, file)
    file.close()

def animal_path_mapping(wdid:str, animal_pattern:str)->dict:
    """Get the path mapping of WikiData object to the Animal class
        Identify the main subclasses the path goes through for easier tree building 
    Args:
        wdid (str): WikiData ID of the object
        animal_pattern (str): Pattern of the path 

    Raises:
        ValueError: Raised if 'animal_pattern' is not a recognized path pattern (taxon, subclass, subclass_taxon_subclass, subclass_instance)

    Returns:
        dict: dict containing the mapping in format :
            - subclass_instance : { superclass:str }
            - taxon : { taxon_superclasses:list[str] }
            - subclass_taxon_subclass : { superclass:str, taxon_superclasses:list[str] }
            - subclass : { superclasses:list[str] }

    """
    match animal_pattern:
        case 'subclass_instance':
            result = SPtools.select_query('SELECT ?class WHERE { wd:'+wdid+' wdt:P31 ?class }',['class'])
            return { 'superclass': result[0]['class'].replace(SPtools.WD_ENTITY_URI, '') }
        
        case 'taxon':
            result = SPtools.select_query('SELECT ?class { wd:'+wdid+' wdt:P171* ?class. ?class wdt:P279* wd:Q729 }', ['class'])
            return { 'taxon_superclasses':[r['class'].replace(SPtools.WD_ENTITY_URI, '') for r in result] }
        
        case 'subclass_taxon_subclass':
            superclass = SPtools.select_query(
                'SELECT ?class WHERE { wd:'+wdid+' wdt:P279 ?class }', ['class']
            )[0]['class'].replace(SPtools.WD_ENTITY_URI, '')
            result = SPtools.select_query('SELECT ?class { wd:'+superclass+' wdt:P171* ?class. ?class wdt:P279* wd:Q729 }', ['class'])
            return {
                'superclass': superclass,
                'taxon_superclasses': [r['class'].replace(SPtools.WD_ENTITY_URI, '') for r in result]
            }
        
        case 'subclass' :
            result = SPtools.select_query('SELECT ?class WHERE { wd:'+wdid+' wdt:P279 ?class }', ['class'])
            return { 'superclasses': [r['class'].replace(SPtools.WD_ENTITY_URI, '') for r in result] }
        case _ :
            raise ValueError('"'+animal_pattern+'" is not a recognized path pattern (taxon, subclass, subclass_taxon_subclass, subclass_instance)')

def create_graph_arcs(synsets:list[dict], tree_structure_file_path:str='Data/graph_arcs.csv', master_parent_node:str='Q729'):
    """Create the arcs of the graph leading each object to a Master parent class. 
        Each wikiData object represents a node, and arcs represent a subclass link.
        Arcs are stored in a csv file with format (parent,child).  

    Args:
        synsets (list[dict]): list of synsets to compute the arcs of.
        tree_structure_file_path (str, optional): Path of the file to store the results in. Defaults to 'Data/graph_arcs.csv'.
        master_parent_node (str, optional): Value of the master parent node to reach. Defaults to 'Q729'.
    
    Raises:
        ValueError: If an animal pattern has an incorrect value
        KeyError: If the synsets have been correctly instantiated. 
            They need 'wdid', a valid 'animal_pattern' and the matching animal path mapping 
    """
    def child_exists(tree_df:pd.DataFrame, child:str)->bool:
        return (tree_df['child']==child).any()
        
    def insert_unique(tree_df:pd.DataFrame, parent:str, child:str)->bool:
        if ((tree_df['parent']==parent) & (tree_df['child']==child)).any():
            return False
        new_row = {
            'parent': parent,
            'child': child
        }
        tree_df.loc[len(tree_df)] = new_row
        return True

    if not os.path.exists(tree_structure_file_path):
        tree_df = pd.DataFrame(columns=['parent', 'child'])
    else:
        tree_df = pd.read_csv(tree_structure_file_path)

    for synset in tqdm(synsets) :
        if not child_exists(tree_df, synset['wdid']):
            try:
                match synset['animal_pattern']:
                    case 'subclass_instance':
                        if not child_exists(tree_df, synset['superclass']):
                            arcs = get_object_subclass_path(synset['superclass'])
                            for arc in arcs:
                                insert_unique(tree_df, arc['parent'], arc['child']) 
                        insert_unique(tree_df, synset['superclass'], synset['wdid'])

                    case 'subclass' :
                        for superclass in synset['superclasses']:
                            if not child_exists(tree_df, superclass):
                                arcs = get_object_subclass_path(superclass)
                                for arc in arcs:
                                    insert_unique(tree_df, arc['parent'], arc['child']) 
                            insert_unique(tree_df, superclass, synset['wdid'])

                    case 'taxon':
                        for node in synset['taxon_superclasses']:
                            if not child_exists(tree_df, node):
                                arcs = get_object_subclass_path(node)
                                for arc in arcs:
                                    insert_unique(tree_df, arc['parent'], arc['child'])
                            if node != master_parent_node:    
                                insert_unique(tree_df, node, synset['wdid'])
                        
                    case 'subclass_taxon_subclass':
                        if not child_exists(tree_df, synset['superclass']):
                            for node in synset['taxon_superclasses']:
                                if not child_exists(tree_df, node):
                                    arcs = get_object_subclass_path(node)
                                    for arc in arcs:
                                        insert_unique(tree_df, arc['parent'], arc['child'])
                                if node != master_parent_node:    
                                    insert_unique(tree_df, node, synset['superclass'])
                        insert_unique(tree_df, synset['superclass'], synset['wdid'])

                    case _ :
                        raise ValueError('Object '+synset['wdid']+' : Pattern "'+synset['animal_pattern']+\
                                         '" is not a recognized path pattern (taxon, subclass, subclass_taxon_subclass, subclass_instance)')
            except Exception as e:

                with open(tree_structure_file_path, 'w') as file:
                    tree_df.to_csv(file, index=False, header=True, lineterminator='\n')
                if type(e) != KeyError:
                    raise e
                message = 'Object '+synset['wdid']+' : Key "'+e.args[0]+'" not set.\n'
                match e.args[0]:
                    case 'animal_pattern':
                        message += 'To set all the animal patterns, run the function ontology_builder.set_all_animal_pattern'
                    case 'superclass' | 'superclasses' | 'taxon_superclasses':
                        message += 'To set all animal path mapping the right way, run the function ontology_builder.set_all_animal_path_mapping'
                raise KeyError(message)
    with open(tree_structure_file_path, 'w') as file:
        tree_df.to_csv(file, index=False, header=True, lineterminator='\n')

def get_object_subclass_path(wdid_child:str, wdid_parent:str='Q729')->list[dict]:
    """Get the path of a WikiData object to one of its parent classes
        Path is represented like the arcs of a graph in which WikiData objects are nodes.
        An Arc is then a parent node and a child node

    Args:
        wdid_child (str): WikiData ID of the child
        wdid_parent (str, optional): WikiData ID of the parent node. Defaults to 'Q729' (Animal node).

    Returns:
        list[dict]: List of arcs in format { parent:str, child:str } 
    """
    query= """
        SELECT ?parent ?child
        WHERE {{
            wd:{child} wdt:P279* ?child.
            ?child wdt:P279 ?parent.
            ?parent wdt:P279* wd:{parent}
        }}
        """.format(child=wdid_child, parent=wdid_parent)
    result = SPtools.select_query(query, ['parent', 'child'])    
    return [{
            'parent': r['parent'].replace(SPtools.WD_ENTITY_URI, ''),
            'child': r['child'].replace(SPtools.WD_ENTITY_URI, '')
        } for r in result]
