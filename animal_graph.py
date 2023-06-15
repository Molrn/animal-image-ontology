import synset_mapper as sm
import Tools.list_dict_tools as LDtools
import Tools.sparql_tools as sp
from csv import DictReader
from tqdm import tqdm
import pandas as pd
import json
import os

ANIMAL_PATTERNS_PATH = 'animal_patterns.json'
GRAPH_ARCS_PATH = 'Data/KaggleChallenge/graph_arcs.csv'
ANIMAL_WDID = 'Q729'

def get_animal_mapping(mapping_file_path:str=sm.FULL_MAPPING_PATH)->list[dict]:
    """Get the animal mapping from its file. If the file doesn't exist, generate it

    Args:
        mapping_file_path (str, optional): Path of the file containing the mapping of all the synsets. Defaults to sm.FULL_MAPPING_PATH.

    Returns:
        list[dict]: List of dict containig the mapping of each animal synset
    """
    synsets = sm.get_synset_full_mapping(mapping_file_path)
    animal_mapping = [s for s in synsets if 'animal_pattern' in s and s['animal_pattern']]
    return animal_mapping  

def get_animal_patterns(wdid:str, pattern_file_path:str=ANIMAL_PATTERNS_PATH)->dict:
    """Get all the animal patterns formatted for a specific WikiData object

    Args:
        wdid (str): ID of the object to format into the patterns
        pattern_file_path (str, optional): Path of the patterns file. Defaults to ANIMAL_PATTERNS_PATH.

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

def set_all_animal_pattern(mapping_file_path:str=sm.FULL_MAPPING_PATH, wdid_start:str=None):
    """Set the pattern of each WikiData object from itself to the Animal class

    Args:
        mapping_file_path (str, optional): Path of the file containing the synsets. 
            When the function generates an error, the computed synsets are stored in that file. 
            Defaults to sm.FULL_MAPPING_PATH.
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
        if sp.ask_query('ASK WHERE { '+pat+' }') :
            return pat_name
    return None

def get_graph_arcs(graph_file_path:str=GRAPH_ARCS_PATH)->list[dict]:
    """Return the arcs of the graph in list[dict] format.
        If it doesn't exist, the graph is created.

    Args:
        graph_file_path (str, optional): Path of the file containing the graph. 
            If it doesn't exist, the graph is created at that path. Defaults to GRAPH_ARCS_PATH.

    Returns:
        list[dict]: arcs of the graph in format list[ { parent:str, child:str, parentLabel:str, childLabel:str } ]
    """
    if not os.path.exists(graph_file_path):
        create_graph_arcs(get_animal_mapping(), graph_file_path)
    with open(graph_file_path, 'r') as f:
        graph_arcs = list(DictReader(f))
    return graph_arcs

def create_graph_arcs(synsets:list[dict], tree_structure_file_path:str=GRAPH_ARCS_PATH, master_parent_node:str=ANIMAL_WDID):
    """Create the arcs of the graph leading each object to a Master parent class. 
        Each wikiData object represents a node, and arcs represent a subclass link.
        Arcs are stored in a csv file with format (parent,child,parentLabel,childLabel).  

    Args:
        synsets (list[dict]): list of synsets to compute the arcs of.
        tree_structure_file_path (str, optional): Path of the file to store the results in. Defaults to GRAPH_ARCS_PATH.
        master_parent_node (str, optional): Value of the master parent node to reach. Defaults to ANIMAL_WDID.
    
    Raises:
        ValueError: If an animal pattern has an incorrect value
        KeyError: If the synsets have been correctly instantiated. 
            They need 'wdid', a valid 'animal_pattern' and the matching animal path mapping 
    """
    def child_exists(tree_df:pd.DataFrame, child:str)->bool:
        return (tree_df['child']==child).any()
        
    def check_insert(tree_df:pd.DataFrame, parent:str, child:str, parent_label:str=None, child_label:str=None)->bool:
        def get_label(label:str, tree_df:pd.DataFrame, wdid:str):
            if not label:
                label_match = tree_df['childLabel'][tree_df['child']==wdid].values
                if len(label_match) != 0:
                    label = label_match[0]
                if not label:
                    label = sm.get_label_mapping([wdid])[0]['label']
            return label
        
        if parent == child or ((tree_df['parent']==parent) & (tree_df['child']==child)).any():
            return False
        new_row = {
            'parent': parent,
            'child': child,
            'parentLabel' : get_label(parent_label, tree_df, parent).title(),
            'childLabel'  : get_label(child_label, tree_df, child).title()
        }
        tree_df.loc[len(tree_df)] = new_row
        return True    

    def add_taxon_path(tree_df:pd.DataFrame, wdid:str, label:str=None, 
                       excluded:list[str]=[], subclass_check:bool=True, wdid_dest:str=ANIMAL_WDID)->bool:
        is_animal = False
        if child_exists(tree_df, wdid):
            return True
        else:
            if subclass_check:
                if add_subclass_path(tree_df, wdid, wdid_dest):
                    return True
            taxon_parents = get_taxon_parents(wdid)
            ordered_parents = taxon_parents.copy()
            is_ordered = False
            while not is_ordered:
                is_ordered = True
                parent_classes = [par['parent'] for par in ordered_parents]
                child_classes = [par['child'] for par in ordered_parents]
                reordered = 0
                for i, parent in enumerate(parent_classes):
                    if parent in child_classes[i:]:
                        is_ordered = False
                        ordered_parents += [ordered_parents.pop(i-reordered)]
                        reordered += 1
            for taxon_par in taxon_parents:
                if child_exists(tree_df, taxon_par['child']):
                    check_insert(tree_df, taxon_par['child'], wdid, taxon_par['childLabel'], label)
                    is_animal = True 
                elif child_exists(tree_df, taxon_par['parent']) or taxon_par['parent'] == wdid_dest:
                    check_insert(tree_df, taxon_par['parent'], taxon_par['child'],taxon_par['parentLabel'], taxon_par['childLabel']) 
                    check_insert(tree_df, taxon_par['child'], wdid, taxon_par['childLabel'], label) 
                    is_animal = True
                else:
                    if taxon_par['parent'] not in excluded and taxon_par['child'] != wdid_dest:
                        is_parent_animal = add_taxon_path(tree_df, taxon_par['parent'], taxon_par['parentLabel'], excluded, wdid_dest)
                        if is_parent_animal :                            
                            check_insert(tree_df, taxon_par['parent'], taxon_par['child'],taxon_par['parentLabel'], taxon_par['childLabel']) 
                            check_insert(tree_df, taxon_par['child'], wdid, taxon_par['childLabel'], label)
                            is_animal = True
                        else:
                            excluded.append(taxon_par['parent'])
        return is_animal

    def add_subclass_path(tree_df:pd.DataFrame, wdid:str, wdid_dest:str=ANIMAL_WDID):
        subclass_path = get_object_subclass_path(wdid, wdid_dest)
        if subclass_path :
            for arc in subclass_path:
                check_insert(tree_df, arc['parent'], arc['child'], arc['parentLabel'], arc['childLabel']) 
            return True 
        return False 

    if not os.path.exists(tree_structure_file_path):
        default_arcs = [
            {'parent':'Q729', 'child':'Q25241', 'parentLabel':'Animal', 'childLabel':'Vertebrata'},
            {'parent':'Q729', 'child':'Q777371', 'parentLabel':'Animal', 'childLabel':'Quadruped'},
            {'parent':'Q777371', 'child':'Q19159', 'parentLabel':'Quadruped', 'childLabel':'Tetrapoda'},
            {'parent':'Q25241', 'child':'Q19159', 'parentLabel':'Vertebrata', 'childLabel':'Tetrapoda'},
            {'parent':'Q19159', 'child':'Q5113', 'parentLabel':'Tetrapoda', 'childLabel':'Birds'},
            {'parent':'Q25241', 'child':'Q152', 'parentLabel':'Vertebrata', 'childLabel':'Fish'},
            {'parent':'Q1756633', 'child':'Q152', 'parentLabel':'Aquatic Animal', 'childLabel':'Fish'},
            {'parent':'Q188438', 'child':'Q5113', 'parentLabel':'Theropod', 'childLabel':'Birds'},
            {'parent':'Q430', 'child':'Q188438', 'parentLabel':'Dinosaur', 'childLabel':'Theropod'},
            {'parent':'Q729', 'child':'Q1756633', 'parentLabel':'Animal', 'childLabel':'Aquatic Animal'}
        ]
        tree_df = pd.DataFrame(default_arcs)
    else:
        tree_df = pd.read_csv(tree_structure_file_path)

    not_animal_classes = []
    for synset in tqdm(synsets) :
        if not child_exists(tree_df, synset['label']):
            try:
                match synset['animal_pattern']:
                    case 'subclass_instance':
                        breed_class = 'wd:Q38829'
                        query = f"""
                            SELECT ?class ?label 
                            WHERE {{ 
                                wd:{synset['wdid']} {sp.INSTANCE_PROP} 
                                                [{sp.SUBCLASS_PROP} ?class].
                                ?class rdfs:label ?label
                                FILTER (?class != {breed_class} && LANG(?label)='en') 
                            }}
                            """
                        superclass = sp.select_query(query,['class', 'label'])[0]
                        superclass_entity = superclass['class'].replace(sp.WD_ENTITY_URI,'')
                        add_subclass_path(tree_df, superclass_entity)
                        check_insert(tree_df, superclass_entity, synset['wdid'], superclass['label'], synset['label'])

                    case 'subclass' :
                        query = f"""
                            SELECT ?class ?label 
                            WHERE {{ 
                                wd:{synset['wdid']} {sp.SUBCLASS_PROP} ?class. 
                                ?class rdfs:label ?label
                                FILTER (LANG(?label)='en') 
                            }}
                            """
                        superclasses = sp.select_query(query, ['class', 'label'])
                        for superclass in superclasses:
                            entity = superclass['class'].replace(sp.WD_ENTITY_URI,'')
                            if add_subclass_path(tree_df, entity):
                                check_insert(tree_df, entity, synset['wdid'], superclass['label'], synset['label'])

                    case 'taxon':
                        add_taxon_path(tree_df, synset['wdid'], synset['label'], not_animal_classes, False)
                        
                    case 'subclass_taxon_subclass':
                        query = f"""
                            SELECT ?class ?classLabel 
                            WHERE {{ 
                                wd:{synset['wdid']} {sp.SUBCLASS_PROP} ?class.
                                ?class rdfs:label ?classLabel  
                                FILTER (LANG(?classLabel)='en')    
                            }}"""
                        superclass = sp.select_query(query, ['class', 'classLabel'])[0]
                        superclass_entity = superclass['class'].replace(sp.WD_ENTITY_URI,'')
                        if not add_taxon_path(tree_df, superclass_entity, superclass['classLabel'], not_animal_classes, False):
                            check_insert(tree_df, master_parent_node, superclass_entity, child_label=superclass['classLabel'])                        
                        check_insert(tree_df, superclass_entity, synset['wdid'], superclass['classLabel'], synset['label'])                        
                        
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

def get_object_subclass_path(wdid_child:str, wdid_parent:str=ANIMAL_WDID)->list[dict]:
    """Get the path of a WikiData object to one of its parent classes
        Path is represented like the arcs of a graph in which WikiData objects are nodes.
        An Arc is then a parent node and a child node. The graph also includes both of their labels

    Args:
        wdid_child (str): WikiData ID of the child
        wdid_parent (str, optional): WikiData ID of the parent node. Defaults to ANIMAL_WDID.

    Returns:
        list[dict]: List of arcs in format { parent:str, child:str, parentLabel:str, childLabel:str } 
    """
    query= f"""
        SELECT ?parent ?child ?parentLabel ?childLabel
        WHERE {{
            wd:{wdid_child} {sp.SUBCLASS_PROP}* ?child.                        
            ?child {sp.SUBCLASS_PROP} ?parent;
                    rdfs:label ?childLabel.
            ?parent {sp.SUBCLASS_PROP}* wd:{wdid_parent};
                    rdfs:label ?parentLabel
            FILTER (LANG(?parentLabel) = 'en' && LANG(?childLabel) = 'en')  
        }}
        """
    result = sp.select_query(query, ['parent', 'child', 'parentLabel', 'childLabel'])    
    return [{
            'parent': r['parent'].replace(sp.WD_ENTITY_URI, ''),
            'child': r['child'].replace(sp.WD_ENTITY_URI, ''),
            'parentLabel': r['parentLabel'].title(),
            'childLabel': r['childLabel'].title()
        } for r in result]

def get_taxon_parents(wdid:str)->list[dict]:
    """Get the parent classes of an object via its taxons. 
        Each taxon parent contains its parent class
    
    Args:
        wdid (str): WikiData ID of the object to get the taxon parents of
    
    Returns:    
        list[dict]: List of arcs in format { parent:str, child:str, parentLabel:str, childLabel:str } 
    """
    query = f"""
        SELECT ?parent ?child ?parentLabel ?childLabel 
        WHERE {{
            wd:{wdid} wdt:P171* ?child.
            ?child wdt:P279 ?parent;
                    rdfs:label ?childLabel.
            ?parent rdfs:label ?parentLabel
            FILTER (LANG(?childLabel) = 'en' && LANG(?parentLabel) = 'en')
        }}"""   
    result = sp.select_query(query, ['parent', 'child', 'parentLabel', 'childLabel'])    
    return [{
            'parent': r['parent'].replace(sp.WD_ENTITY_URI, ''),
            'child': r['child'].replace(sp.WD_ENTITY_URI, ''),
            'parentLabel': r['parentLabel'].title(),
            'childLabel': r['childLabel'].title()
        } for r in result]
