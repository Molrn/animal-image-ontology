from SPARQLWrapper import SPARQLWrapper, JSON
import list_dict_tools as LDtools
import sparql_tools as SPtools
from nltk.corpus import wordnet as wn
import os
import json

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
        [inid, synset] = line.split(' ', 1)
        synset = synset.split(', ') 
        synsets.append({
            'inid' : str(inid),
            'wnid' : get_new_wnid(synset, wn_version),
            'synset' : synset
        })
    wnwd_map = bulk_select_wdids_from_wnids(list(set([s['wnid'] for s in synsets])))
    synsets = LDtools.ld_join(synsets, wnwd_map, 'wnid', 'left')
    synsets_wn = [s for s in synsets if s['wdid'] is not None]
    synsets_in = [s for s in synsets if s['wdid'] is None]
    for s in synsets_in:
        del s['wdid']
    inwd_map = bulk_select_wdids_from_inids([s['inid'] for s in synsets_in])
    synsets_in = LDtools.ld_join(synsets_in, inwd_map, 'inid', 'left')
    synsets = synsets_wn+synsets_in

    output_file = open(output_path, 'w')
    json.dump(synsets,output_file)
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
    print('Warning: Synset '+str(synset)+' not found')
    return ''

def bulk_select_wdids_from_wnids(wnids:list[str], step=400)->list[dict]:
    """Get the WikiData IDs of objects matching WordNet objects. 
    Goes through the properties 'WordNet 3.1 Synset ID' (P8814)

    Args:
        wnids (list[str]): list of IDs of the WordNet objects to match. Has to be in WordNet version 3.1 format
        step (int, optional): Number of WD IDs to fetch per query. Defaults to 400.

    Returns:
        list[dict]: list of dict in format {wnid:str, wdid:str} 
    """
    query = """
        SELECT ?wdid ?wnid 
        WHERE {{ 
            VALUES ?wnid {{ {} }}. 
            ?wdid wdt:P8814 ?wnid 
        }}
        """
    mapping = SPtools.bulk_select(wnids, query, ['wdid', 'wnid'], 'str', step)
    wd_entity_uri = 'http://www.wikidata.org/entity/'    
    for m in mapping:
        m['wdid'] = m['wdid'].replace(wd_entity_uri, '')
    return mapping

def bulk_select_wdids_from_inids(inids:list[str], step=400)->list[dict]:
    """Get the WikiData IDs of objects matching ImageNet IDs (WordNet ids version 3.0). 
    Goes through the properties 'exact match' (P2888)

    Args:
        inids (list[str]): list of IDs of the ImageNet objects to match.
        step (int, optional): Number of WD IDs to fetch per query. Defaults to 400.

    Returns:
        list[dict]: list of dict in format {inid:str, wdid:str} 
    """
  
    wd_entity_uri = 'http://www.wikidata.org/entity/'
    wn_uri = 'http://wordnet-rdf.princeton.edu/wn30/'
    wn_prefix = 'wn:'
    prefix_str = "PREFIX "+wn_prefix+" <"+wn_uri+">"
    query = """
        SELECT ?wdid ?inid
        WHERE {{ 
            VALUES ?inid {{ {} }}. 
            ?wdid wdt:P2888 ?inid 
        }}
        """
    mapping = SPtools.bulk_select([inid.replace('n', '')+'-n' for inid in inids], 
                            prefix_str+query, ['wdid', 'inid'], wn_prefix, step)
    wd_entity_uri = 'http://www.wikidata.org/entity/'    
    for m in mapping:
        m['wdid'] = m['wdid'].replace(wd_entity_uri, '')
        m['inid'] = m['inid'].replace(wn_uri, '').replace('-n', '')
    return mapping

def set_all_synsets_manual_wdid(mapping_path:str='Data/synset_mapping.json', inid_start:str=None):
    """Manually set the WikiData IDs of the synsets who don't have one

    Args:
        mapping_path (str, optional): Path of the file containing the synsets. 
            When the function generates an error, the computed synsets are stored in that file. 
            Defaults to 'Data/synset_mapping.json'.
        inid_start (str, optional): ImageNet ID of the synsets to start from. Defaults to None.
    """
    synsets = get_synset_full_mapping(mapping_path)
    start_index = 0
    if inid_start:
        start_index = next((i for i, s in enumerate(synsets) if s['inid']==inid_start), 0)
    synsets = LDtools.apply_to_all_dicts(
        synsets,
        manual_wdid,
        ['synset'],
        'wdid',
        mapping_path,
        start_index)

    file = open(mapping_path, 'w')
    json.dump(synsets, file)
    file.close()

def manual_wdid(synset:list[str])->str:
    """Manually fetch the WikiData ID of a synset from its lemmas.
        Fetch all IDs and description of WD objects having an alias or a label matching one lemma.
        When multiple objects are found, display their description and let the user decide which object to choose.

    Args:
        synset (list[str]): List of lemmas identifying an ImageNet object.

    Returns:
        str: WikiData ID of the user chosen object
    """
    wd_entity_uri = 'http://www.wikidata.org/entity/'
    for lemma_i, lemma in enumerate(synset) :
        matching_objects = wd_label_search(lemma)
        if len(matching_objects) == 0:
            if lemma != lemma.title():
                matching_objects = wd_label_search(lemma.title())
        if len(matching_objects) == 1:
            return matching_objects[0]['wdid']
        elif len(matching_objects) != 0:
            print('\nSynset : '+', '.join(synset))
            for i , object in enumerate(matching_objects):
                print(i, ': \033]8;;'+wd_entity_uri+object['wdid']+'\033\\'+object['desc']+'\033]8;;\033\\')
            if lemma_i == len(synset)-1:
                print('-1 : None')
            else:
                print('-1 : Change lemma')
            print('-2 : Manual input\n')
            choice = -3
            while int(choice) not in list(range(len(matching_objects)))+[-1, -2]:
                choice = input('Select a new wdid : ')
            if int(choice) == -2:
                return input('New wdid : ')
            if int(choice) != -1:
                return matching_objects[int(choice)]['wdid']
    return None

def wd_label_search(search:str)->list[dict]:
    """Search for a string in WikiData labels and aliases 
    
    Args:
        search (str): string to research

    Returns:
        list[dict]: list of dicts in format wdid:str, desc:str}. 
            Each dict contains the ID and the description of one of the object found
    """
    query = """
            SELECT ?wdid ?desc
            WHERE {{
                VALUES ?prop {{ skos:altLabel rdfs:label }}
                ?wdid ?prop "{search}"@en;
                schema:description ?desc.
                FILTER(LANG(?desc) = "en") 
            }}
            """.format(search=search)
    result = SPtools.select_query(query, ['wdid', 'desc'])
    wd_entity_uri = 'http://www.wikidata.org/entity/'
    for r in result:
        r['wdid'] = r['wdid'].replace(wd_entity_uri, '')
    return r

