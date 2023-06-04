from SPARQLWrapper import SPARQLWrapper, JSON
from nltk.corpus import wordnet as wn
import pandas as pd
import os
import json

def bulk_collect_wdids_from_wnids(wnids:list[str], step=400)->list[dict]:
    """Get the WikiData IDs of objects matching WordNet objects 

    Args:
        wnids (list[str]): list of IDs of the WordNet objects to match. Has to be in WordNet version 3.1 format
        step (int, optional): Number of WD IDs to fetch per query. Defaults to 400.

    Returns:
        list[dict]: list of dict in format {wnid:str, wdid:str} 
    """
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
    sparql.setReturnFormat(JSON)
    wnid_prop = 'wdt:P8814'
    wd_entity_uri = 'http://www.wikidata.org/entity/'
    start_index = 0
    full_mapping = []
    while start_index < len(wnids):
        end_index = min(start_index+step, len(wnids))
        wnid_query_str = '"'+'" "'.join(wnids[start_index:end_index])+'"'
        query = "SELECT ?wdid ?wnid WHERE { VALUES ?wnid { "+wnid_query_str+" }. ?wdid "+wnid_prop+" ?wnid }"
        sparql.setQuery(query)
        result = sparql.query().convert()['results']['bindings']
        full_mapping += [{
            'wnid' : r['wnid']['value'],
            'wdid' : r['wdid']['value'].replace(wd_entity_uri, '')
        } for r in result]
        start_index = end_index
    return full_mapping

def get_synset_full_mapping(mapping_path='Data/synset_mapping.json')->list[dict]:
    """Get the mapping of each synset in WikiData, ImageNet and WordNet

    Args:
        mapping_path (str, optional): Path of the file containing the mapping. 
            If the file doesn't exist, the mapping file is created at this path. Defaults to 'Data/synset_mapping.json'.

    Returns:
        list[dict]: list of dict in format {synset:list[str], inid:str, wnid:str, wdid:str}
    """
    if not os.path.exists(mapping_path):
        generate_synset_full_mapping(output_path=mapping_path)
    mapping_file = open(mapping_path)
    mapping_dict = json.load(mapping_file)
    mapping_file.close()
    return mapping_dict

def generate_synset_full_mapping(input_path='Data/LOC_synset_mapping.txt', output_path='Data/synset_mapping.json'):
    """Generate a json file mapping synsets in WikiData, ImageNet and WordNet

    Args:
        input_path (str, optional): path of the file containing a list of synsets and ImageNet IDs. Defaults to 'Data/LOC_synset_mapping.txt'.
        output_path (str, optional): path of the file to generate the json mapping into. Defaults to 'Data/synset_mapping.json'.
    """
    input_file = open(input_path)
    lines = input_file.readlines()
    input_file.close()
    synsets = []
    wn_version = wn.get_version()
    for line in lines:
        line = line.replace('\n', '')
        [wnid, synset] = line.split(' ', 1)
        synset = synset.split(', ') 
        synsets.append({
            'inid' : str(wnid),
            'wnid' : get_new_wnid(synset, wn_version),
            'synset' : synset
        })
    wd_mapping = bulk_collect_wdids_from_wnids([s['wnid'] for s in synsets])
    
    synset_df = pd.DataFrame(synsets)
    map_df = pd.DataFrame(wd_mapping)
    synset_df = synset_df.join(map_df.set_index('wnid'), 'wnid')
    output_file = open(output_path, 'w')
    synset_df.to_json(output_file, orient='records')
    output_file.close()

def get_new_wnid(synset:list[str], wn_version=None):
    """Get the WordNet ID of a synset in format WordNet 3.1

    Args:
        synset (list[str]): list of lemmas of the synset
        wn_version (str, optional): WordNet version. Useful for performance issues in bulk operations. Defaults to None.

    Raises:
        ImportError: Raised if the current WordNet version is lower than 3.1 
        ValueError: Raised if the synset isn't found

    Returns:
        str: WordNet ID of the synset in format WordNet 3.1
    """
    if (wn.get_version() if not wn_version else wn_version) < '3.1':
        raise ImportError('Current WordNet version does not provide the requested operation\n'+
                    '\tWordNet IDs compatible with WikiData only are available in versions 3.1 or higher\n'+
                    '\tDatabase files for WordNet 3.1 are avaliable at this URL: https://wordnet.princeton.edu/download/current-version')
    
    compare_synset = [x.replace(' ', '_') for x in synset] 
    synset_search_list = wn.synsets(compare_synset[0])
    for search_item in synset_search_list:
        if set(compare_synset) == set(search_item.lemma_names()): 
            return str(search_item.offset()).zfill(8)+'-n'
    raise ValueError('Synset '+str(synset)+' not fount')
