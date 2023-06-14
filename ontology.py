from tqdm import tqdm
from zipfile import ZipFile
from shutil import rmtree
import os
from Tools.sparql_tools import WD_ENTITY_URI
from animal_graph import get_graph_arcs, get_animal_mapping, GRAPH_ARCS_PATH
from synset_mapper import FULL_MAPPING_PATH
from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDFS, RDF, XSD, FOAF
from rdflib.term import Node, BNode
import json
import xmltodict
from tqdm import tqdm
import random

ZIP_FILE_PATH       = 'imagenet-object-localization-challenge.zip'
IMAGES_PATH         = 'Data/Images/'
ANNOT_PATH          = 'Data/Annotations/' 
TEST_DIR            = 'Test/'
TRAIN_DIR           = 'Train/'
ANNOT_TRAIN_PATH    = ANNOT_PATH+TRAIN_DIR
ANNOT_TEST_PATH     = ANNOT_PATH+TEST_DIR
IMAGES_TRAIN_PATH   = IMAGES_PATH+TRAIN_DIR
IMAGES_TEST_PATH    = IMAGES_PATH+TEST_DIR
ONTOLOGY_FILE_PATH  = 'Data/KaggleChallenge/animal_ontology.ttl'
MORPH_FEATURES_PATH = 'Data/KaggleChallenge/animal_features.json'
SCHEMA_IRI          = 'http://schema.org/'
ONTOLOGY_IRI        = 'http://www.semanticweb.org/youri/ontologies/2023/5/animal-challenge/'
ANIMAL_LABEL        = 'Animal'
IMAGE_FILE_EXT      = '.JPEG'
ANNOT_FILE_EXT      = '.xml'

def create_ontology(output_file_path:str=ONTOLOGY_FILE_PATH,
                    graph_file_path:str=GRAPH_ARCS_PATH,
                    morph_features_file_path:str=MORPH_FEATURES_PATH,
                    mapping_file_path:str=FULL_MAPPING_PATH,
                    master_node_label:str=ANIMAL_LABEL)->Graph:
    """User interface to create the ontology. it is saved in Turtle format in an output file 

    Args:
        output_file_path (str, optional): Path to store the ontology file at. Defaults to ONTOLOGY_FILE_PATH.
        graph_file_path (str, optional): Path of the csv file containing the graph arcs. Defaults to GRAPH_ARCS_PATH.
        morph_features_file_path (str, optional): Path of the json file containing the features per animal class. Defaults to MORPH_FEATURES_PATH.
        master_node_label (str, optional): Label of the master node of the ontology. Defaults to 'Animal'.

    Returns:
        Graph: Created ontology
    """
    print('Initializing the structure...', end='')
    ontology = initialize_ontology_structure(graph_file_path, morph_features_file_path, mapping_file_path, master_node_label)
    print('Done')
    populate = input('Populate the ontology (5 minutes per 100 animal classes)? (y/N)')
    if populate == 'y':
        splitted = input('Have you splitted the Images/Annotations files into train and test ? (y/N)')
        if splitted != 'y':
            unzipped = input('Have you unzipped the challenge images zip file ? (y/N)')
            if unzipped != 'y':  
                downloaded = input('Have you downloaded the challenge images zip file ? (y/N)')
                if downloaded != 'y':
                    print('Ontology can not be populated without the challenge zip file, please download it before going any further')
                    print('\nTo download the zip file containing the animal_images :')
                    print('\t1) Go to https://www.kaggle.com/competitions/imagenet-object-localization-challenge/rules and accept the rules')
                    print('\t2) Go to https://www.kaggle.com/settings/account and generate an API token')
                    print('\t3) Place the generated kaggle.json file in this diectory')
                    print('\t4) execute this command : kaggle competitions download -c imagenet-object-localization-challenge')
                    ontology.serialize(output_file_path)
                    print('Structure ontology saved to file "'+output_file_path+'"')
                    return ontology
                zip_file_path = input(f'Zip file path (default: {ZIP_FILE_PATH}) : ')
                if zip_file_path == 'default':
                    zip_file_path = ZIP_FILE_PATH
                ac = Namespace(ONTOLOGY_IRI)
                ontology_inids = [inid for _, _, inid in ontology.triples((None, ac.inid, None))]
                print('Unzipping images and annotations...')
                unzip_images_annotations_files(ontology_inids, zip_file_path)

            rate = input('Test splitting rate (0<rate<1): ')            
            print('Splitting files into train and test')
            train_test_split(float(rate))

        print('Populating the ontology...')
        ontology = populate_ontology(ontology)
    print('Saving the ontology to file "'+output_file_path+'"...', end='')
    ontology.serialize(output_file_path)
    print('Done')
    return ontology

def initialize_ontology_structure(graph_file_path:str=GRAPH_ARCS_PATH,
                        morph_features_file_path:str=MORPH_FEATURES_PATH,
                        mapping_file_path:str=FULL_MAPPING_PATH,
                        master_node_label:str=ANIMAL_LABEL):
    """Pipeline initializing the ontology structure step by step

    Args:
        graph_file_path (str, optional): Path of the csv file containing the graph. Defaults to 'Data/graph_arcs.csv'.
        morph_features_file_path (str, optional): Path of the file containing the morphological features dictionnary. Defaults to MORPH_FEATURES_PATH.
        master_node_label (str, optional): Label of the master node of the graph. Defaults to ANIMAL_LABEL.
    """
    ontology = Graph()
    ac = Namespace(ONTOLOGY_IRI)
    wd = Namespace(WD_ENTITY_URI)
    schema = Namespace(SCHEMA_IRI)
    ontology.bind('ac', ac)
    ontology.bind('wd', wd)
    ontology.bind('schema', schema)
    
    ontology = define_properties(ontology, ac)

    graph_arcs = get_graph_arcs(graph_file_path)
    class_labels = list(set([a['childLabel'] for a in graph_arcs] + [master_node_label]))
    
    for label in class_labels:
        ontology.add((label_to_node(label, ac), RDF.type, RDFS.Class))   

    # define the subclass of features (=structure of the graph)
    for arc in graph_arcs:
        child_node = label_to_node(arc['childLabel'], ac)
        parent_node = label_to_node(arc['parentLabel'], ac)
        ontology.add((child_node, RDFS.subClassOf, parent_node))    
        
    for node in [label_to_node(label, ac) for label in class_labels]:
        parents = [o for _, _, o in ontology.triples((node, RDFS.subClassOf, None))]        
        removed = set([])
        for parent1 in parents:
            parent1_parents = [parent for parent in ontology.transitive_objects(parent1, RDFS.subClassOf)] 
            for parent2 in parents:
                if parent1 != parent2 and parent2 not in removed and parent1 not in removed:
                    #parent2_parents = [o for _, _, o in ontology.triples((parent2, RDFS.subClassOf, None))] 
                    if parent2 in parent1_parents:
                        ontology.remove((node, RDFS.subClassOf, parent2))
                        removed.add(parent2)

    # define the ImageNed ID and WikiData ID of each node
    for synset in get_animal_mapping(mapping_file_path):
        if synset['label'] in class_labels :
            node = label_to_node(synset['label'], ac)
            ontology.add((node, ac.inid, Literal(synset['inid'])))
            ontology.add((node, ac.wdid, getattr(wd, synset['wdid'])))

    ontology = define_morphological_features(ontology, morph_features_file_path)
    return ontology

def get_ontology(ontology_file_path:str=ONTOLOGY_FILE_PATH)->Graph:
    """Load the ontology from a local file. If it doesn't exist, intialize the ontology.

    Args:
        ontology_file_path (str, optional): Path of the file containing the ontolology. 
            The ontology is created in this file if it doesn't exist. Defaults to ONTOLOGY_FILE_PATH.

    Returns:
        Graph: Full animal ontology
    """
    if not os.path.exists(ontology_file_path):
        print('No file at path "'+ontology_file_path+'", creating the ontology instead')
        return create_ontology(ontology_file_path)
    ontology = Graph()
    ontology.parse(ontology_file_path)
    return ontology
    
def define_properties(ontology:Graph, ns:Namespace)->Graph:
    """Define all the required properties into a ontology

    Args:
        ontology (Graph): ontology of the propertie
        ns (Namespace): Namespace to define the properties in
    """
    properties = [ 'inid', 'wdid', 'boundingBox', 'xMin', 'xMax', 'yMin', 'yMax', 
                  'difficult', 'pose', 'truncated', 'hasMorphFeature',
                  'size', 'height', 'width', 'depth' ]
    for property in properties :
        ontology.add((getattr(ns, property), RDF.type, RDF.Property))

    for bnd_prop in ['xMin', 'xMax', 'yMin', 'yMax']:
        ontology.add((getattr(ns, bnd_prop), RDFS.range, XSD.positiveInteger))
        ontology.add((getattr(ns, bnd_prop), RDFS.domain, ns.boundingBox))

    for size_prop in ['height', 'width', 'depth']:
        ontology.add((getattr(ns, size_prop), RDFS.range, XSD.positiveInteger))
        ontology.add((getattr(ns, size_prop), RDFS.domain, ns.size))

    ontology.add((ns.inid, RDFS.range, XSD.string))
    ontology.add((ns.hasMorphFeature, RDFS.range, ns.MorphFeature))

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
        Graph: ontology with all classes, all subclass property, initialized 
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

    ontology.add((ac.MorphFeature, RDF.type, RDFS.Class))
    for feature, class_nodes in all_features.items():
        if len(class_nodes) > 1:
            ontology.add((feature, RDF.type, ac.MorphFeature))
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

def populate_ontology(ontology:Graph, images_dir_path:str=IMAGES_TRAIN_PATH, annot_dir_path:str=ANNOT_TRAIN_PATH)->Graph: 
    """Populate the ontology with objects from the images of each class
        The link from images to ontology class is made through the Image Net ID

    Args:
        ontology (Graph): Ontology with the structure initialized
        images_dir_path (str, optional): Path of the directory containing the images. Defaults to IMAGES_TRAIN_PATH.
        annot_dir_path (str, optional): Path of the directory containing the annotations. Defaults to ANNOT_TRAIN_PATH.

    Returns:
        Graph: Populated ontology
    """
    ac = Namespace(ONTOLOGY_IRI)
    schema = Namespace(SCHEMA_IRI)

    nb_classes = len([inid for _, _, inid in ontology.triples((None, ac.inid, None))])
    pbar = tqdm(ontology.triples((None, ac.inid, None)), total=nb_classes)
    for class_node, _, inid in pbar:
        animal_img_dir_path = images_dir_path+inid
        animal_annot_dir_path = os.path.join(annot_dir_path, inid)
        if not os.path.exists(animal_img_dir_path):
            print('Warning : no images for class '+str(class_node).replace(ONTOLOGY_IRI,'')+" ("+inid+')')
        else:        
            im = Namespace('file:///'+os.path.abspath(animal_img_dir_path).replace('\\', '/')+'/')
            images = os.listdir(animal_img_dir_path)
            nb_img = len(images)
            for img_index, image in enumerate(images):
                pbar.set_description(f"Processing {inid} ({img_index}/{nb_img})")
                image_path_node = getattr(im, image)
                image_node = getattr(ac, 'IMG_'+image.replace(IMAGE_FILE_EXT, ''))
                annotation_path = os.path.join(animal_annot_dir_path, image.replace(IMAGE_FILE_EXT, ANNOT_FILE_EXT))
                if os.path.exists(annotation_path):
                    with open(annotation_path) as annotation_file:
                        annotation = xmltodict.parse(annotation_file.read())['annotation']
                    define_image_node(ontology, image_node, image_path_node, ac, schema, annotation['size'])

                    if 'object' in annotation:
                        if type(annotation['object'])==list:
                            for i, object in enumerate(annotation['object']):
                                animal_node = getattr(ac, image.replace(IMAGE_FILE_EXT, '_'+str(i)))
                                define_animal_node(ontology, animal_node, class_node, image_node, ac, object)
                        else :
                            animal_node = getattr(ac, image.replace(IMAGE_FILE_EXT,''))
                            define_animal_node(ontology, animal_node, class_node, image_node, ac, annotation['object'])
                else:
                    define_image_node(ontology, image_node, image_path_node, ac, schema)
                    animal_node = getattr(ac, image.replace(IMAGE_FILE_EXT,''))
                    define_animal_node(ontology, animal_node, class_node, image_node, ac)
    return ontology

def define_animal_node(ontology:Graph, node:Node, class_node:Node, 
                  image_node:Node, prop_ns:Namespace, annotations:dict=None):
    """define an animal node in the ontology

    Args:
        ontology (Graph): Ontology to define the node in
        node (Node): URI Ref of the node to create
        class_node (Node): Node of the class of the Animal
        image_node (Node): Node of the image it appears on
        prop_ns (Namespace): Namespace of the properties
        annotations (dict, optional): Object in the xml file annoting the image and defining the instance animal on the image. 
            Defaults to None.
    """
    ontology.add((node, RDF.type, class_node))
    ontology.add((node,FOAF.img,image_node))
    if annotations :
        bndbox_node = BNode()
        bndbox = annotations['bndbox']
        ontology.add((node, prop_ns.boundingBox, bndbox_node))
        ontology.add((bndbox_node, prop_ns.xMin, Literal(int(bndbox['xmin']))))
        ontology.add((bndbox_node, prop_ns.yMin, Literal(int(bndbox['ymin']))))
        ontology.add((bndbox_node, prop_ns.xMax, Literal(int(bndbox['xmax']))))
        ontology.add((bndbox_node, prop_ns.yMax, Literal(int(bndbox['ymax']))))

def define_image_node(ontology:Graph, image_node:Node, image_path_node:Node, 
                      ac:Namespace, schema:Namespace, size:dict=None):

    ontology.add((image_node, RDF.type, schema.ImageObject))
    image_url = BNode()
    ontology.add((image_node, schema.image, image_url))
    ontology.add((image_url, RDF.type, schema.URL))
    ontology.add((image_url, schema.value, image_path_node))

    if size:
        size_node = BNode()
        ontology.add((image_node, ac.size, size_node))
        ontology.add((size_node, ac.width, Literal(int(size['width']))))
        ontology.add((size_node, ac.height, Literal(int(size['height']))))
        ontology.add((size_node, ac.depth, Literal(int(size['depth']))))

def unzip_images_annotations_files(inids:list[str], zip_file_path:str=ZIP_FILE_PATH, 
                                   images_dest_path:str=IMAGES_PATH, annotations_dest_path:str=ANNOT_PATH):
    """Unzip the images and annotations files of the selected ids from the Kaggle Challenge Zip file

    Args:
        inids (list[str]): list of ImageNet IDs of the resources to extract
        zip_file_path (str, optional): path of the Kaggle Challenge Zip file. Defaults to ZIP_FILE_PATH.
        images_dest_path (str, optional): Path of the Images destination directory. Defaults to IMAGES_PATH.
        annotations_dest_path (str, optional): Path of the Images destination directory. Defaults to ANNOT_PATH.

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
    zip_annot_path = 'ILSVRC/Annotations/CLS-LOC/train/'
    zip_images_path =  'ILSVRC/Data/CLS-LOC/train/'
    with ZipFile(zip_file_path, 'r') as zip_file:
        for inid in tqdm(inids):
            for zip_subdirectory, destination_path in [
                    (os.path.join(zip_annot_path,inid), os.path.join(annotations_dest_path,inid)),
                    (os.path.join(zip_images_path, inid), os.path.join(images_dest_path,inid))                    
                ]:
                if not os.path.exists(destination_path):
                    for file_name in [name for name in zip_file.namelist() if name.startswith(zip_subdirectory)]:
                        extracted_path = os.path.join(destination_path, os.path.basename(file_name))
                        zip_file.extract(file_name, destination_path)
                        os.rename(os.path.join(destination_path, file_name), extracted_path)
                    rmtree(os.path.join(destination_path, 'ILSVRC')) 

def train_test_split(
            test_rate           :float,
            images_origin_path  :str=IMAGES_PATH, 
            annot_origin_path   :str=ANNOT_PATH,
            images_train_path   :str=IMAGES_TRAIN_PATH,
            annot_train_path    :str=ANNOT_TRAIN_PATH,
            images_test_path    :str=IMAGES_TEST_PATH,
            annot_test_path     :str=ANNOT_TEST_PATH
        ):
    """Split the annotations and images into train and test directories according to a test_rate  

    Args:
        test_rate (float): Rate according to which an image is added to the test directory. 0 < test_size < 1. 
        images_origin_path (str, optional): Path of the directory containing the images. Defaults to IMAGES_PATH.
        annot_origin_path (str, optional): Path of the directory containing the annotations. Defaults to ANNOT_PATH.
        images_train_path (str, optional): Path of the directory into which the training images will be moved. Defaults to IMAGES_TRAIN_PATH.
        annot_train_path (str, optional): Path of the directory into which the training annotations will be moved. Defaults to ANNOT_TRAIN_PATH.
        images_test_path (str, optional): Path of the directory into which the testing images will be moved. Defaults to IMAGES_TEST_PATH.
        annot_test_path (str, optional): Path of the directory into which the testing images will be moved. Defaults to ANNOT_TEST_PATH.

    Raises:
        ValueError: if the directory at images_origin_path doesn't exist
    """
    
    for path in [images_origin_path, annot_origin_path]:
        if not os.path.exists(path):
            raise ValueError('Path '+path+'doesn\'t exist\n'+
                'If you haven\'t done it, unzip the required images from the challenge Zip file at this location\n'+
                'You can do so by running the function "unzip_images_annotations_files"')
    try:
        os.mkdir(images_train_path)
        os.mkdir(images_test_path)
        os.mkdir(annot_train_path)
        os.mkdir(annot_test_path)
    except FileExistsError:
        None
    for inid in tqdm(os.listdir(images_origin_path)):
        animal_image_dir = os.path.join(images_origin_path, inid)
        animal_annot_dir = os.path.join(annot_origin_path, inid)
        if os.path.normpath(animal_image_dir) not in [
                        os.path.normpath(images_test_path), 
                        os.path.normpath(images_train_path)]:   
            try:
                os.mkdir(os.path.join(images_train_path, inid))
                os.mkdir(os.path.join(images_test_path, inid))
                os.mkdir(os.path.join(annot_train_path, inid))
                os.mkdir(os.path.join(annot_test_path, inid))
            except FileExistsError:
                None
            for image in os.listdir(animal_image_dir):
                if random.random() > test_rate:
                    image_dest_path = os.path.join(images_train_path, inid, image)
                    annot_dest_path = os.path.join(annot_train_path, inid, image.replace(IMAGE_FILE_EXT, ANNOT_FILE_EXT))
                else:
                    image_dest_path = os.path.join(images_test_path, inid, image)
                    annot_dest_path = os.path.join(annot_test_path, inid, image.replace(IMAGE_FILE_EXT, ANNOT_FILE_EXT))
                os.rename(os.path.join(animal_image_dir, image), image_dest_path)
                annot_file_path = os.path.join(animal_annot_dir, image.replace(IMAGE_FILE_EXT, ANNOT_FILE_EXT))
                if os.path.exists(annot_file_path):
                    os.rename(annot_file_path, annot_dest_path)
            os.rmdir(animal_image_dir)
            os.rmdir(animal_annot_dir)

def graphs():
    # TODO Display the ontology into graphs
    # export the results into a directory called 'Exports'
    # Display graphs with rdflib : https://rdflib.readthedocs.io/en/stable/intro_to_graphs.html
    # Graph ideas :
    #   - Full display of all the classes
    #   - Display of all the classes that have subclasses, and give to the node of each class the size of the number of direct subclasses it has
    return
