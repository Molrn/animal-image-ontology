import synset_mapper as sm
import ontology_builder as ob
import ontology_populator as op

# A : Full Mapping of the synsets
# Map as well as possible the synsets in 3 different applications : ImageNet, Wordnet (different from ImageNet since version 3.1), WikiData
# the result is stored in the Data/synset_mapping.json file

## 1 : Initialize the file (mapping ImageNet ID-->WordNet 3.1 ID, then use both ids to get the Max automated WikiData IDs) 
sm.generate_synset_full_mapping()

## 2 : Set all of synsets with no match manually. The lemmas of each synset are searched in the WikiData aliases and labels.
# Each object found is displayed with its description, and the user has to choose the most appropriate object
# As it requires a lot of API calls, the program might stop for a 'Too many requests' error. 
# When it does so, the computed results are saved in the Data/synset_mapping.json file.
# Function has to be ran until there no longer is any unmapped value
sm.set_all_synsets_manual_wdid()

## 3 : Remap the object that are common name of others 
synsets = sm.get_synset_full_mapping()
sm.remap_common_name_of(synsets)

# B : Identify the patterns of each Animal from his WikiData URI to the Animal Class
# This step will allow us to build an tree structure from the animal class to all of our animal objects 

## 1 : Identify the animals in the synsets
# Has to be ran multiple times just like step A.2 for API limitation reasons 
ob.set_all_synsets_animal_status()

## 2 : Generate the Data/animal_synsets.json file from the Data/synset_mapping.json file
ob.get_animal_mapping()

## 3 : Set the patterns of all the animals
# Has to be ran multiple times for API limitation reasons 
ob.set_all_animal_pattern()

# C : Build the Animal ontology
## 1 : Get the path mapping of the each object to the Animal class
# Fetch the key parent classes of each synset in order
# As to run multiple times as well
ob.set_all_animal_path_mapping() 

## 2 : Generate the graph Arcs
# Create a CSV file containing two columns, parent and child
ob.create_graph_arcs(ob.get_animal_mapping())

# D : Populate the ontology
## 1 : Download Animal Images and Annotations
# Download the Challenge zip file on Kaggle
# Unzip the Animal resources to 'Data/Annotations' and 'Data/Images' directories 
animal_synsets = ob.get_animal_mapping()
op.unzip_images_annotations_files([s['inid'] for s in animal_synsets])
