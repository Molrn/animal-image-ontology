from ontology import ONTOLOGY_IRI, get_ontology, IMAGES_TEST_PATH, IMAGES_TRAIN_PATH, ONTOLOGY_STRUCTURE_FILE_PATH
from rdflib import Graph, Namespace
from rdflib.namespace import RDFS, RDF
from sklearn.ensemble import RandomForestClassifier
from sklearn.base import BaseEstimator
from pandas import DataFrame, Series, read_csv
import cv2
import os
from tqdm import tqdm

FEATURES_PREDICTION_FILE_PATH = 'Data/KaggleChallenge/features_prediction.csv'

def image_recognition_model(
        ontology_file_path:str=ONTOLOGY_STRUCTURE_FILE_PATH,
        images_train_dir_path:str=IMAGES_TRAIN_PATH, 
        images_test_dir_path:str=IMAGES_TEST_PATH,        
        features_prediction_file_path:str=FEATURES_PREDICTION_FILE_PATH,
        animal_classifier:BaseEstimator=None,
        morph_features_prediction_classifier:BaseEstimator=None):
    """Train and evaluate an image recognition model by predicting an DataFrame of morphological features for the test images

    Args:
        ontology_file_path (str, optional): Path of the ontology file. Defaults to ONTOLOGY_FILE_PATH.
        images_train_dir_path (str, optional): Path of the directory containing the training images. Defaults to IMAGES_TRAIN_PATH.
        images_test_dir_path (str, optional): Path of the directory containing the testing images. Defaults to IMAGES_TEST_PATH.
        features_prediction_file_path (str, optional): Path of the file to save the features prediction Dataframe into. 
            Defaults to FEATURES_PREDICTION_FILE_PATH.
        animal_classifier (BaseEstimator, optional): Classifier used to train and evaluate the model. 
            Defaults to RandomForestClassifier.
        morph_features_prediction_classifier (BaseEstimator, optional): Classifier used to predict the morphological features of the test images. 
            Defaults to RandomForestClassifier.
    """
    ontology = get_ontology(ontology_file_path)
    ac = Namespace(ONTOLOGY_IRI)
    inids = [str(inid) for _, _, inid in ontology.triples((None, ac.inid, None))]
    inid_mapping = {inid: i+1 for i, inid in enumerate(inids)}
    
    morph_features_df = build_class_morph_features_df(ontology)
    x_morph_features = morph_features_df[morph_features_df.columns.drop('inid')]
    y_morph_features = morph_features_df['inid'].map(inid_mapping)

    compute_prediction = True
    if os.path.exists(features_prediction_file_path):
        compute_prediction = False
        print('File "'+features_prediction_file_path+'" already exists')
        comp_pred_input = input('Compute prediction again ? (y/N)')
        if comp_pred_input == 'y':
            compute_prediction = True

    if compute_prediction:
        print('Initialize a training and a testing dataset from the animal images')
        x_train, x_test, y_train, y_test = get_images_test_train(
            images_train_dir_path, images_test_dir_path, inids)

        y_train_encoded = y_train.map(inid_mapping)
        y_test_encoded = y_test.map(inid_mapping)      

        print('Predict the morphological features of the test dataset...')
        x_test_morph_features = predict_all_columns_df(
                                    x_test, x_train, y_train_encoded, 
                                    x_morph_features, y_morph_features,
                                    morph_features_prediction_classifier)
        x_test_morph_features.to_csv(features_prediction_file_path, index=False)
    else: 
        x_test_morph_features = read_csv(features_prediction_file_path)

    if not animal_classifier:
        animal_classifier = RandomForestClassifier()
    print('Training model...', end='')
    animal_classifier.fit(x_morph_features, y_morph_features)
    print('Done')
    print('Model accuracy : {:.3f}'.format(animal_classifier.score(x_test_morph_features, y_test_encoded)))

def get_images_test_train(train_dir_path:str=IMAGES_TRAIN_PATH,
                          test_dir_path:str=IMAGES_TEST_PATH,
                          inids:list[str]= []
                          )->tuple[DataFrame, DataFrame, Series, Series]:
    """Extract a training and testing dataset from the images

    Args:
        train_dir_path (str, optional): path of the directory containing the training images. Defaults to IMAGES_TRAIN_PATH.
        test_dir_path (str, optional): path of the directory containing the testing images. Defaults to IMAGES_TEST_PATH.
        inids (list[str], optional): List of ImageNet IDs to get the images of. 
            If empty, images are gathered from all of the sudirectories in the images directories are taken. Defaults to [].

    Returns:
        tuple[DataFrame, DataFrame, Series, Series]: 
            Features and target for the train and test datasets
    """
    def extract_image_dataset(images_dir_path:str, inids:list[str])->tuple[DataFrame, Series]:
        features = []
        target = []
        for inid in tqdm((inids if inids else os.listdir(images_dir_path))):
            object_dir_path = os.path.join(images_dir_path, inid)
            if not os.path.exists(object_dir_path):
                raise ValueError('ImageNet ID "'+inid+'" directory not found at path "'+object_dir_path+'"')
            for image in os.listdir(object_dir_path):
                features.append(extract_image_features(os.path.join(object_dir_path, image)))
                target.append(inid)
        return DataFrame(features), Series(target)
    
    print('Extract training dataset...')
    x_train, y_train = extract_image_dataset(train_dir_path, inids)
    print('Extract testing dataset...')
    x_test, y_test = extract_image_dataset(test_dir_path, inids)
    return x_train, x_test, y_train, y_test

def build_class_morph_features_df(ontology: Graph)->DataFrame:
    """Build a DataFrame containing all of the morphological features per animal class and the ImageNet ID of the animal

    Args:
        ontology (Graph): Ontology to fetch the features and the animal classes into

    Returns:
        DataFrame: DataFrame with one column per morphological feature and one column for the ImageNet ID named 'inid'.
            There is one row per class containing a ac:inid property in the ontology
    """
    ac = Namespace(ONTOLOGY_IRI)
    morph_features = [feature for feature, _, _ in ontology.triples((None, RDF.type, ac.MorphFeature))]
    all_animal_features = []
    for animal_class, _, inid in ontology.triples((None, ac.inid, None)):
        animal_row = { 'inid' : str(inid) }
        animal_features = [feature for _, _, feature in ontology.triples((animal_class, ac.hasMorphFeature, None))]
        for feature in morph_features:
            animal_row[feature.replace(ONTOLOGY_IRI, '')] = (feature in animal_features)
        all_animal_features.append(animal_row)
    return DataFrame(all_animal_features)

def extract_image_features(image_path:str):
    """Extract an array of features from an image

    Args:
        image_path (str): Path of the image to get the features of

    Returns:
        ndarray: array of shape(512, ) containing the features of the image
    """
    image = cv2.imread(image_path)
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv_image], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    hist = cv2.normalize(hist, hist).flatten()
    return hist

def predict_all_columns_df(x_to_predict:DataFrame,
                           x_train:DataFrame, y_train:Series, 
                           x_from_predict:DataFrame, y_from_predict:Series, 
                           classifier:BaseEstimator=None)->DataFrame:
    """Create a Dataframe by predicting all the columns of another dataset ('from' dataset).
    Each prediction is made from a model trained by the features of a dataset and its target 
    mapped to a column of the 'from' dataset according to the 'from' target
    Target of the 'from' dataset and the training target has to have similar values

    Args:
        x_to_predict (DataFrame): used to predict each column of the generated DataFrame
        x_train (DataFrame): Features used for training the model predicting each column 
        y_train (Series): Target to be mapped by y_from_predict to generate the training Target.
            All of the distinct values must be included in y_from_predict.
        x_from_predict (DataFrame): Dataframe containing all the columns to predict into the new Dataframe.
            Each column is mapped to y_train using y_from_predict and used as the target of the training model
        y_from_predict (Series): Target of the Dataframe to predict the columns of
        classifier (BaseEstimator, optional): Classifier to use to generate the prediction. Defaults to None.

    Raises:
        ValueError: If the target "y_train" contains a value which is not in the "y_from_predict" target

    Returns:
        DataFrame: Prediction of every column of x_from_predict applied to every row of x_to_predict
    """
    from_uniques = y_from_predict.unique()
    for train_val in y_train.unique():
        if train_val not in from_uniques:
            raise ValueError('Target "y_train" contains a value ('+train_val+') which is not in the "y_from_predict" target')
    if not classifier:
        classifier = RandomForestClassifier()
    predicted_df = DataFrame()
    progress_bar = tqdm(x_from_predict.columns)
    for column in progress_bar:
        progress_bar.set_description('Predicting "'+column+'"')
        mapping_dict = dict(zip(y_from_predict, x_from_predict[column]))
        y_to_predict_train = y_train.map(mapping_dict)
        classifier.fit(x_train, y_to_predict_train)
        column_prediction = classifier.predict(x_to_predict)
        predicted_df[column] = column_prediction

    return predicted_df 
