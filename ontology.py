from tqdm import tqdm
from zipfile import ZipFile
from shutil import rmtree
import os
import Tools.sparql_tools as SPtools
from animal_graph import get_graph_arcs, get_animal_mapping, GRAPH_ARCS_PATH, ANIMAL_WDID

# TODO Complete the constants
ZIP_FILE_PATH = 'imagenet-object-localization-challenge.zip'
IMAGES_PATH = 'Data/Images'
ANNOTATIONS_PATH = 'Data/Annotations'
ONTOLOGY_IRI        = "" 
SUBCLASS_PROPERTY   = 'rdfs:subClassOf'
LABEL_PROPERTY      = 'rdfs:label'
INSTANCE_PROPERTY   = 'rdfs:instanceOf'
INID_PROPERTY       = ''
HAS_PROPERTY        = ''
MORPHOLOGICAL_FEATURE_CLASS=""

def initialize_ontology(graph_file_path:str=GRAPH_ARCS_PATH, master_node:str=ANIMAL_WDID):
    """Pipeline initializing the ontology step by step

    Args:
        graph_file_path (str, optional): Path of the csv file containing the graph. Defaults to 'Data/graph_arcs.csv'.
        master_node (str, optional): WikiData ID of the master node. Defaults to 'Q729' (Animal ID).
    """
    create_ontology()
    graph_arcs = get_graph_arcs(graph_file_path, master_node)
    class_nodes = list(set(
        [a['child'] for a in graph_arcs] + 
        [master_node] + 
        [synset['wdid'] for synset in get_animal_mapping()]
    ))
    define_classes(class_nodes)
    create_properties()

    # define the subclass of all the objects 
    for arc in graph_arcs:
        set_triplet(arc['child'], SUBCLASS_PROPERTY, arc['parent'])  

    # define the properties of each node
    for synset in get_animal_mapping():
        set_triplet(synset['wdid'], INID_PROPERTY, '"'+synset['inid']+'"')
        set_triplet(synset['wdid'], LABEL_PROPERTY, '"'+synset['label']+'"')
    
    define_morphological_features()

def create_ontology(iri:str=ONTOLOGY_IRI):
    """Create the ontology

    Args:
        iri (str, optional): IRI of the ontology. Defaults to ONTOLOGY_IRI.
    """
    # TODO Create the ontology at the IRI ONTOLOGY_IRI
    # hint : Mohamed / Youssef used rdflib
    # they created the ontology by sending triplets to an ontology located at an IRI and it allowed them to easily display graphs
    # doc : https://rdflib.readthedocs.io/en/stable/gettingstarted.html

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

def define_classes(classes:list[str]):
    """Define the classes of the graph

    Args:
        classes (list[str]): List of classes ID to add to the graph
    """
    # TODO 

def define_morphological_features(class_name:str=MORPHOLOGICAL_FEATURE_CLASS):
    # TODO Create the class in the ontology
    # TODO Create Instances of the class (ex : museau, patte, aile, bec, queue, poil, plume)
    # TODO using the 'has' property, define manually which great class has the feature (ex: bird has feathers)
    # Implies some kind of research on every class, or we could use chatGPT to generate it 
    # Besides specific animal object, there are 76 nodes, it would be great if it was done on all of them
    # results could be fetched from WikiData using this property :https://www.wikidata.org/wiki/Property:P1552
    # Let me know if you find it relevant, I'll write the function to get it 
    return

def create_properties():
    # TODO create all the properties that are not default ones (ex: INID_PROPERTY)
    return

def set_triplet(subject:str, property:str, object:str):
    """Sets the value of a triplet in the ontology

    Args:
        subject (str): Subject of the triplet
        property (str): Property of the triplet
        object (str): Object of the triplet
    """
    # TODO 

def graphs():
    # TODO Display the ontology into graphs
    # export the results into a directory called 'Exports'
    # Display graphs with rdflib : https://rdflib.readthedocs.io/en/stable/intro_to_graphs.html
    # Graph ideas :
    #   - Full display of all the classes
    #   - Display of all the classes that have subclasses, and give to the node of each class the size of the number of direct subclasses it has
    return

def sparql_query(query:str, is_select:bool=True):
    # TODO Execute a SPARQL Query into the graph
    # Functions from SPtools might be used
    return
