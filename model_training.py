import ontology as onto


def train_test_split()->tuple[list, list[str], list, list[str]]:
    """Split the nodes into train and test datasets, get the features and characteristics

    Returns:
        tuple[list, list[str], list, list[str]]: 
            Features and target for the train and test datasets
    """
    test_inids = ['n02114367', 'n01484850', 'n01614925', 'n02133161',  'n01537544', 'n01443537']
    test_inids_query_str = ' '.join(['"'+inid+'"' for inid in test_inids])
    test_query = """
        SELECT ?wdid
        WHERE {{
            VALUES ?inid {{ {inids} }}
            ?wdid {inid_prop} ?inid 
        }}
        """.format(
                inids=test_inids_query_str,
                label_prop=onto.LABEL_PROPERTY,
                inid_prop=onto.INID_PROPERTY
            )
    train_query = """
        SELECT ?wdid ?label
        WHERE {{
            VALUES ?inid {{ {inids} }}
            ?wdid {label_prop} ?label 
            FILTER NOT EXISTS {{ ?wdid {inid_prop} ?inid }} 
        }}
        """.format(
                inids=test_inids_query_str,
                label_prop=onto.LABEL_PROPERTY,
                inid_prop=onto.INID_PROPERTY
            )

    test_result = onto.sparql_query(test_query)
    train_result = onto.sparql_query(train_query)

    y_test  = [r['label'] for r in test_result]
    y_train = [r['label'] for r in train_result]

    test_nodes =  [r['wdid'].replace(onto.ONTOLOGY_IRI, '') for r in test_result]
    train_nodes = [r['wdid'].replace(onto.ONTOLOGY_IRI, '') for r in train_result]    
    
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
