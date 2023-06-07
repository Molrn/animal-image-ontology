from tqdm import tqdm
from zipfile import ZipFile
from shutil import rmtree
import os

def unzip_images_annotations_files(inids:list[str], zip_file_path:str='imagenet-object-localization-challenge.zip', 
                                   images_dest_path:str='Data/Images', annotations_dest_path:str='Data/Annotations'):
    """Unzip the images and annotations files of the selected ids from the Kaggle Challenge Zip file

    Args:
        inids (list[str]): list of ImageNet IDs of the resources to extract
        zip_file_path (str, optional): path of the Kaggle Challenge Zip file. Defaults to 'imagenet-object-localization-challenge.zip'.
        images_dest_path (str, optional): Path of the Images destination directory. Defaults to 'Data/Images'.
        annotations_dest_path (str, optional): Path of the Images destination directory. Defaults to 'Data/Annotations'.

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
