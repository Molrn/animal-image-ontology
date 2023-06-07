from typing import Callable
import json
import pandas as pd
from pprint import pprint
from time import sleep
from tqdm import tqdm

def apply_to_all_dicts(dict_list:list[dict], function:Callable, 
                        arg_keys:list[str], return_key:str=None, 
                        error_save_path:str='Data/temp_dict_list.json',
                        start_index:int=0, stop_index:int=None, delay:float=None)->list[dict]:
    """Apply a function to all the dicts of a list. 
        If an error occurs, the list is saved into a temporary file

    Args:
        dict_list (list[dict]): List of dicts to apply the function to
        function (Callable): function to apply to each dict. 
            If parameter 'return_key' is None, has to return a dict.
        arg_keys (list[str]): keys of the arguments to five to the function. 
            Key name must be the same as the function parameter
        return_key (str, optional): key of the dictionnary to save the result in.   
            Function only will be executed if the key value in the dict is None.
            If 'return_key' is None, all the values of the result will be added to the dict.
            Parameter 'function' then has to return a dict.
            Defaults to None.
        error_save_path (str, optional): Path of the file to save the dict into in case of an error. 
            Defaults to 'Data/temp_dict_list.json'.
        start_index (int, optional): index of the list to start the search from. Defaults to 0.
        stop_index (int, optional): index of the list to stop the search at. Defaults to None.
        delay (float, optional): time between each run, in seconds. Defaults to None.

    Returns:
        list[dict]: list of dicts with the function applied to each dict 
    """
    run_nb = 0
    for dic in tqdm(dict_list[start_index:stop_index]):
        if dic['animal_pattern']=='subclass' and 'subclasses' not in dic:
        #return_key is None or return_key not in dic or dic[return_key] is None:
            run_nb += 1
            arg_dict = {}
            for key in arg_keys:
                arg_dict[key] = dic[key]
            try:
                result = function(**arg_dict)
            except Exception as e :
                save_file = open(error_save_path, 'w')
                json.dump(dict_list, save_file)
                save_file.close()
                print('\nProgram successfully ran '+str(run_nb-1)+' times')
                print('Last dict : ')
                pprint(dic)            
                raise e
            if return_key is None:
                for key, value in result.items():
                    dic[key] = value
            else :
                dic[return_key] = result
            if delay:
                sleep(delay)
    return dict_list

def ld_join(left_list:list[dict], right_list:list[dict], on:str, join_type='inner'):
    """Left join two lists of dictionnaries according to one column using pandas  

    Args:
        left_list (list[dict]): Left part of the join (fully returned)
        left_list (list[dict]): Right part of the join (matching returned)
        on (str): column present in each record of both dicts

    Returns:
        list[dict]: joined list of dicts
    """
    left_df = pd.DataFrame(left_list)
    right_df = pd.DataFrame(right_list)
    full_df = left_df.join(right_df.set_index(on), on, how=join_type)
    full_df = full_df.where(pd.notnull(full_df), None)
    return full_df.to_dict('records')
