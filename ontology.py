from tqdm import tqdm
from zipfile import ZipFile
from shutil import rmtree
import os
from Tools.sparql_tools import WD_ENTITY_URI
from animal_graph import get_graph_arcs, get_animal_mapping, GRAPH_ARCS_PATH
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDFS, RDF, XSD
from rdflib.term import Node
import json

ZIP_FILE_PATH       = 'imagenet-object-localization-challenge.zip'
IMAGES_PATH         = 'Data/Images'
ANNOTATIONS_PATH    = 'Data/Annotations' 
ONTOLOGY_FILE_PATH  = 'Data/animal_ontology.ttl'
MORPH_FEATURES_PATH = 'Data/animal_features.json'
ONTOLOGY_IRI        = 'http://example.com/ontology/animal-challenge/'
ANIMAL_LABEL        = 'Animal'

def initialize_ontology(ontology_file_path:str=ONTOLOGY_FILE_PATH, 
                        graph_file_path:str=GRAPH_ARCS_PATH,
                        morph_features_file_path:str=MORPH_FEATURES_PATH,
                        master_node_label:str=ANIMAL_LABEL):
    """Pipeline initializing the ontology step by step

    Args:
        graph_file_path (str, optional): Path of the csv file containing the graph. Defaults to 'Data/graph_arcs.csv'.
        morph_features_file_path (str, optional): Path of the file containing the morphological features dictionnary. Defaults to MORPH_FEATURES_PATH.
        master_node_label (str, optional): Label of the master node of the graph. Defaults to ANIMAL_LABEL.
    """

    ontology = Graph()
    ac = Namespace(ONTOLOGY_IRI)
    wd = Namespace(WD_ENTITY_URI)
    ontology.bind('ac', ac)
    ontology.bind('wd', wd)
    
    graph_arcs = get_graph_arcs(graph_file_path)
    class_labels = list(set([a['childLabel'] for a in graph_arcs] + [master_node_label]))
    
    for label in class_labels:
        ontology.add((label_to_node(label, ac), RDF.type, RDFS.Class))   

    # define the subclass of features (=structure of the graph)
    for arc in graph_arcs:
        ontology.add((
            label_to_node(arc['childLabel'], ac), 
            RDFS.subClassOf, 
            label_to_node(arc['parentLabel'], ac)
        ))    

    # define the ImageNed ID and WikiData ID of each node
    ontology.add((ac.inid, RDF.type, RDF.Property))
    ontology.add((ac.inid, RDFS.range, XSD.string))
    ontology.add((ac.wdid, RDF.type, RDF.Property))
    for synset in get_animal_mapping():
        if synset['label'] in class_labels :
            node = label_to_node(synset['label'], ac)
            ontology.add((node, ac.inid, Literal(synset['inid'])))
            ontology.add((node, ac.wdid, getattr(wd, synset['wdid'])))

    ontology = define_morphological_features(ontology, morph_features_file_path)
    ontology.serialize(ontology_file_path)

def get_ontology(ontology_file_path:str=ONTOLOGY_FILE_PATH)->Graph:
    """Load the ontology from a local file. If it doesn't exist, intialize the ontology.

    Args:
        ontology_file_path (str, optional): Path of the file containing the ontolology. 
            The ontology is created in this file if it doesn't exist. Defaults to ONTOLOGY_FILE_PATH.

    Returns:
        Graph: Full animal ontology
    """
    if not os.path.exists(ontology_file_path):
        initialize_ontology()
    ontology = Graph()
    ontology.parse(ontology_file_path)
    return ontology
    
def define_morphological_features(ontology:Graph, morph_features_path=MORPH_FEATURES_PATH)->Graph:
    """Define the morphological features of all the nodes

    Args:
        ontology (Graph): ontology
        morph_features_path (str, optional): path of the file containing the morphological features. 
            file has to be a json file in format { "Animal label":list[features(str)] }
            Defaults to MORPH_FEATURES_PATH.

    Raises:
        ValueError: If morphological features file is not found

    Returns:
        Graph: ontology with all classes, all subclass property,  initialized, 
    """
    ac = Namespace(ONTOLOGY_IRI)
    if not os.path.exists(morph_features_path):
        raise ValueError('File "'+morph_features_path+'" not found\n'+
                         'If you don\'t have one, generate it manually as a json file in format dict { "Animal Class Name" : list[str] }\n'+
                         'The animal class name is then matched as the english label found in WikiData')
    with open(MORPH_FEATURES_PATH) as morph_file:
        animal_features = json.load(morph_file)

    all_features = {}
    for animal, features in animal_features.items():
        node = label_to_node(animal, ac)
        if not node :
            print('Warning : '+animal+' not found')
        else:
            for feature in features:
                property = feature_to_property(feature, ac)
                if property not in all_features:
                    all_features[property] = set([node])
                all_features[property] = get_subclasses_set(ontology, all_features[property], node)

    for feature, class_nodes in all_features.items():
        if len(class_nodes) > 1:
            for node in list(class_nodes):
                ontology.add((node, ac.hasMorphFeature, feature))
    return ontology

def label_to_node(label:str, namespace:Namespace)->URIRef:
    """Convert the RDFS label of a node to its URI. 
        URI are in format Namespace_URI + label in PascalCase 

    Args:
        label (str): RDFS label of the object
        namespace (Namespace): namespace of the object 

    Returns:
        URIRef: URI of the matching node
    """
    return getattr(namespace, label.replace("'", '').title().replace('-', '').replace(' ', ''))

def feature_to_property(feature:str, namespace:Namespace)->URIRef:
    """Convert a feature to a property URI. 
        URI are in format Namespace_URI + feature in camelCase 

    Args:
        label (str): RDFS label of the object
        namespace (Namespace): namespace of the object 

    Returns:
        URIRef: URI of the matching property
    """
    property = feature.replace('-', ' ').title().replace(' ', '')
    property = ''.join([property[0].lower(), property[1:]])
    return getattr(namespace, property)

def get_subclasses_set(ontology:Graph, subclass_node_set:set[URIRef], node:Node)->set[URIRef]:
    """Fetch all the subclasses of a node recursively

    Args:
        ontology (Graph): Ontology with classes and suclasses relationships initialized 
        subclass_node_set (set[URIRef]): set of URI to which the subclasses of the node will be added
        node (Node): node to fetch the subclasses of

    Returns:
        set[URIRef]: set of subclasses URI of the node and previous URI in the subclass_node_set
    """
    for subject, _, _ in ontology.triples((None, RDFS.subClassOf, node)):
        if subject not in subclass_node_set: 
            subclass_node_set.add(subject)
            subclass_node_set = get_subclasses_set(ontology, subclass_node_set, subject)
    return subclass_node_set

def populate_ontology():
    # TODO For each image, create an instance of its class with a link to the annotation file some how 
    # instead of a link to the file, it might be more relevant to extract the properties of each annotations file and upload them individually
    # upload an XML file to a dict : https://www.digitalocean.com/community/tutorials/python-xml-to-json-dict
    # 
    return

def unzip_images_annotations_files(inids:list[str], zip_file_path:str=ZIP_FILE_PATH, 
                                   images_dest_path:str=IMAGES_PATH, annotations_dest_path:str=ANNOTATIONS_PATH):
    """Unzip the images and annotations files of the selected ids from the Kaggle Challenge Zip file

    Args:
        inids (list[str]): list of ImageNet IDs of the resources to extract
        zip_file_path (str, optional): path of the Kaggle Challenge Zip file. Defaults to ZIP_FILE_PATH.
        images_dest_path (str, optional): Path of the Images destination directory. Defaults to IMAGES_PATH.
        annotations_dest_path (str, optional): Path of the Images destination directory. Defaults to ANNOTATIONS_PATH.

    Raises:
        ValueError: Raised if the path 'zip_file_path' doesn't exist. If so, the procedure to download the zip file is explained
    """
    if not os.path.exists(zip_file_path):
        raise ValueError('Path '+zip_file_path+'doesn\'t exist\n'+
                         'If you haven\'t downloaded the file yet, here are the steps to follow:\n'+
                         '\t1) Go to https://www.kaggle.com/competitions/imagenet-object-localization-challenge/rules and accept the rules'+
                         '\t2) Go to https://www.kaggle.com/settings/account and generate an API token'+
                         '\t3) Place the generated kaggle.json file in this diectory'+ 
                         '\t4) execute this command : kaggle competitions download -c imagenet-object-localization-challenge')
    zip_annotations_path = 'ILSVRC/Annotations/CLS-LOC/train/'
    zip_images_path =  'ILSVRC/Data/CLS-LOC/train/'
    with ZipFile(zip_file_path, 'r') as zip_file:
        for inid in tqdm(inids):
            for zip_subdirectory, destination_path in [
                    (os.path.join(zip_annotations_path,inid), os.path.join(annotations_dest_path,inid)),
                    (os.path.join(zip_images_path, inid), os.path.join(images_dest_path,inid))                    
                ]:
                if not os.path.exists(destination_path):
                    for file_name in [name for name in zip_file.namelist() if name.startswith(zip_subdirectory)]:
                        extracted_path = os.path.join(destination_path, os.path.basename(file_name))
                        zip_file.extract(file_name, destination_path)
                        os.rename(os.path.join(destination_path, file_name), extracted_path)
                    rmtree(os.path.join(destination_path, 'ILSVRC')) 

def graphs():
    # TODO Display the ontology into graphs
    # export the results into a directory called 'Exports'
    # Display graphs with rdflib : https://rdflib.readthedocs.io/en/stable/intro_to_graphs.html
    # Graph ideas :
    #   - Full display of all the classes
    #   - Display of all the classes that have subclasses, and give to the node of each class the size of the number of direct subclasses it has
    return
