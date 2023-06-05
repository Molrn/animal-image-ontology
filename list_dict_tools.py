from typing import Callable
import json
import pandas as pd
import pprint
from urllib.error import HTTPError

def apply_to_all_dicts(dict_list:list[dict], function:Callable, 
                        arg_keys:list[str], return_key:str, 
                        error_save_path:str='Data/temp_dict_list.json',
                        start_index:int=0)->list[dict]:
    """Apply a function to all the dicts of a list. 
        If an error occurs, the list is saved into a temporary file

    Args:
        dict_list (list[dict]): List of dicts to apply the function to
        function (Callable): function to apply to each dict
        arg_keys (list[str]): keys of the arguments to five to the function. 
            Key name must be the same as the function parameter
        return_key (str): key of the dictionnary to save the result in. 
            Function only will be executed of the key doesn't exist or has a None value
        error_save_path (str, optional): Path of the file to save the dict into in case of an error. 
            Defaults to 'Data/temp_dict_list.json'.
        start_index (int): index of the list to start the search from. Defaults to 0.

    Returns:
        list[dict]: list of dicts with the function applied to each dict 
    """
    run_nb = 0
    for dic in dict_list[start_index:]:
        if return_key not in dic or dic[return_key] is None:
            run_nb += 1
            arg_dict = {}
            for key in arg_keys:
                arg_dict[key] = dic[key]
            try:
                dic[return_key] = function(**arg_dict)
            except Exception as e :
                save_file = open(error_save_path, 'w')
                json.dump(dict_list, save_file)
                save_file.close()
                print('Program ran '+str(run_nb)+' times')
                print('Last dict : ')
                pprint.pprint(dic)            
                if type(e) == HTTPError:
                    print('\n',e.headers)
                raise e
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
