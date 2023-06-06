import synset_mapper as sm
import list_dict_tools as LDtools
import sparql_tools as SPtools
import json
import time
import os

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



def get_animal_synset_mapping():
    synsets = sm.get_synset_full_mapping()
    return [s for s in synsets if s['is_animal']]

