import synset_mapper as sm
import list_dict_tools as LDtools
import sparql_tools as SPtools
import json
import os

def get_animal_mapping(animal_path:str='Data/animal_synsets.json')->list[dict]:
    """Get the animal mapping from its file. If the file doesn't exist, generate it

    Args:
        animal_path (str, optional): Path of the file containing the animal mapping. Defaults to 'Data/animal_synsets.json'.

    Returns:
        list[dict]: List of dict containig the mapping of each animal synset
    """
    if not os.path.exists(animal_path):
        synsets = sm.get_synset_full_mapping()
        animal_mapping = [s for s in synsets if s['is_animal']]
        for syn in animal_mapping:
            syn.pop('is_animal')
        animal_file = open(animal_path, 'w')
        json.dump(animal_mapping, animal_file)
        animal_file.close()
        return animal_file
    animal_file = open(animal_path)
    animal_mapping = json.load(animal_file)
    animal_file.close()
    return animal_mapping    

def set_all_synsets_animal_status(mapping_path:str='Data/synset_mapping.json', inid_start:str=None):
    """Manually set the WikiData IDs of the synsets who don't have one

    Args:
        mapping_path (str, optional): Path of the file containing the synsets. 
            When the function generates an error, the computed synsets are stored in that file. 
            Defaults to 'Data/synset_mapping.json'.
        inid_start (str, optional): ImageNet ID of the synsets to start from. Defaults to None.
    """
    synsets = sm.get_synset_full_mapping(mapping_path)
    start_index = 0
    if inid_start:
        start_index = next((i for i, s in enumerate(synsets) if s['inid']==inid_start), 0)
    synsets = LDtools.apply_to_all_dicts(
        synsets,
        is_animal,
        ['wdid'],
        'is_animal',
        mapping_path,
        start_index)

    file = open(mapping_path, 'w')
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

def set_all_animal_pattern(mapping_path:str='Data/animal_synsets.json', wnid_start:str=None):
    """Set the pattern of each WikiData object from itself to the Animal class

    Args:
        mapping_path (str, optional): Path of the file containing the synsets. 
            When the function generates an error, the computed synsets are stored in that file. 
            Defaults to 'Data/synset_mapping.json'.
        wnid_start (str, optional): WordNet ID of the synsets to start from. Defaults to None.
    """
    synsets = sm.get_synset_full_mapping(mapping_path)
    start_index = 0
    if wnid_start:
        start_index = next((i for i, s in enumerate(synsets) if s['wnid']==wnid_start), 0)
    synsets = LDtools.apply_to_all_dicts(
        synsets,
        get_object_pattern,
        ['wdid'],
        'animal_pattern',
        mapping_path,
        start_index)
    file = open(mapping_path, 'w')
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
