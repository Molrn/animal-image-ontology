import synset_mapper as sm
import animal_graph as ag
import ontology as onto
import model_training as mt


def full_commented_pipeline():
    # A : Full Mapping of the synsets
    # Map as well as possible the synsets in 3 different applications : ImageNet, Wordnet (different from ImageNet since version 3.1), WikiData
    # the result is stored in the Data/synset_mapping.json file

    ## 1 : Initialize the file (mapping ImageNet ID-->WordNet 3.1 ID, then use both ids to get the Max automated WikiData IDs) 
    sm.generate_synset_full_mapping()

    ## 2 : Set all of synsets with no match manually. The lemmas of each synset are searched in the WikiData aliases and labels.
    # Each object found is displayed with its description, and the user has to choose the most appropriate object
    # As it requires a lot of API calls, the program might stop for a 'Too many requests' error. 
    # When it does so, the computed results are saved in the Data/KaggleChallenge/synset_mapping.json file.
    # Function has to be ran until there no longer is any unmapped value
    sm.set_all_synsets_manual_wdid()

    ## 3 : Remap the object that are common name of others 
    synsets = sm.get_synset_full_mapping()
    sm.remap_common_name_of(synsets)

    # B : Build Animal graph structure
    # Using WikiData's SubClassOf and ParentTaxon properties, create a tree with as root the Animal class and as leaves the WikiData objects of our synsets

    ## 1 : Set the label of each WikiData object
    # For more clarity, the graph is built using the labels of the objects instead of their ID
    sm.set_all_labels()        

    ## 2 : Set the patterns to the Animal class for all the objects
    # There are 4 distinct patterns : subclass, taxon, subclass_instance and subclass_taxon_subclass
    # Not animal synsets get a None value, which allows us to identify the animal an not animal synsets 
    # Has to be ran multiple times for API limitation reasons 
    ag.set_all_animal_pattern()

    ## 3 : Generate the graph Arcs
    # Create a CSV file containing two columns, parent and child, and their label, at path Data/KaggleChallenge/graph_arcs.csv
    # Also has to run multiple times for API limitation reasons
    ag.create_graph_arcs(ag.get_animal_mapping())

    # C : Build the ontology
    # This part can be executed as once by using the ontology.create_ontology() function 

    ## 1 : Initialize the morphological features
    # Create the 'Data/KaggleChallenge/animal_features.json' file
    # The file must contain a dictionnary in format { 'animal label': list[str(features)] }
    # each animal Label has to match the ones in the graph_arcs file
    # This file can be created manually, in our case it was generated using ChatGPT

    ## 2 : Create the ontology structure
    # The structure includes all of the classes in the graph_arcs file linked by a subClassOf property and the morphological features of the class
    # it also defines all of the necessary properties
    onto.initialize_ontology_structure()

    ## 3 : Populate the ontology 
    # Add instances of each class as individuals appearing on images

    ### a : Download the file from Kaggle
    # 1) Go to https://www.kaggle.com/competitions/imagenet-object-localization-challenge/rules and accept the rules
    # 2) Go to https://www.kaggle.com/settings/account and generate an API token
    # 3) Place the generated kaggle.json file in this directory
    # 4) execute this command : kaggle competitions download -c imagenet-object-localization-challenge  
    
    ### b : Unzip the Animal resources to 'Data/Annotations' and 'Data/Images' directories 
    animal_synsets = ag.get_animal_mapping()
    onto.unzip_images_annotations_files([s['inid'] for s in animal_synsets])

    ### c : Split the images into testing and training datasets
    onto.train_test_split(0.1) 

    ### d : Populate the ontology with training images
    ontology = onto.get_ontology()
    onto.populate_ontology(ontology)
    ontology.serialize('Data/KaggleChallenge/animal_ontology.ttl')

    # D : Train a model on the ontology

def poc_full_pipeline():
    loc_mapping = 'Data/POC/LOC_synset_mapping.txt'
    mapping_path = 'Data/POC/synset_mapping.json'
    graph_path = 'Data/POC/graph_arcs.csv'
    animal_features_path = 'Data/POC/animal_features.json'
    animal_ontology_path = 'Data/POC/animal_ontology.ttl'

    print('Automatically map synsets to WikiData object')
    sm.generate_synset_full_mapping(loc_mapping, mapping_path)
    print('Initialize manually the WikiData object of the remaining synsets')
    sm.set_all_synsets_manual_wdid(mapping_path)
    print('Get the label of every object from WikiData')
    sm.set_all_labels(mapping_path)
    print('Set the pattern of each animal from his WikiData object to the animal class')
    ag.set_all_animal_pattern(mapping_path)
    print('Create the arc of the graph of the ontology')
    synsets = ag.get_animal_mapping(mapping_path)
    ag.create_graph_arcs(synsets, graph_path)
    print('Create the ontology')
    onto.create_ontology(animal_ontology_path, graph_path, animal_features_path, mapping_path)
    
if __name__=='__main__':
    poc_full_pipeline()
