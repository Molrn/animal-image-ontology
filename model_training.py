import ontology as onto
from rdflib import Graph, Namespace
from rdflib.namespace import RDFS

def train_test_split(ontology:Graph)->tuple[list, list[str], list, list[str]]:
    """Split the nodes into train and test datasets, get the features and characteristics

    Returns:
        tuple[list, list[str], list, list[str]]: 
            Features and target for the train and test datasets
    """
    ac = Namespace(onto.ONTOLOGY_IRI)
    y_test = []
    y_train = []
    test_nodes = []
    train_nodes = []
    
    test_inids = ['n02114367', 'n01484850', 'n01614925', 'n02133161',  'n01537544', 'n01443537']
    for wdid, _, inid in ontology.triples((None, ac.inid, None)):
        label = ontology.value(wdid, RDFS.label)
        if inid in test_inids:
            y_test.append(label)
            test_nodes.append(wdid)
        else:
            y_train.append(label)
            train_nodes.append(wdid)

    # TODO Compute x_test and x_train
    # If you tell me exactly what you need from the ontology and in which format, I can help you extract the data
    # Compute from test_nodes and train_nodes
    x_test  = ''
    x_train = ''
    
    return x_test, y_test, x_train, y_train

# TODO figure out how to train a model from the ontology
# hint : réseau de neurones par convolution (one of the groups uses it)
# --> extract data from the ontology, then train ?
# --> maybe look for it on sklearn ?
# --> check how to train models from images
# If we compare to predictive models we know, I think that :
#   - y value (target) is the class id 
#   - x (features) should contain the images, the parent classes and the morphological features
# From what I understood, the ontology should only contain training values

# TODO Evaluate the model  
# if sklearn or equivalent : score function 
# Otherwise : predict the result for all of the test values and compute manually the different rates

# TODO Trace an RoC curve
