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
                        master_node_label:str=ANIMAL_LABEL):
    """Pipeline initializing the ontology step by step

    Args:
        graph_file_path (str, optional): Path of the csv file containing the graph. Defaults to 'Data/graph_arcs.csv'.
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
