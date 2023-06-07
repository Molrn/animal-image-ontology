from SPARQLWrapper import SPARQLWrapper, JSON

def bulk_select(values_list:list[str], unformatted_query:str, return_keys:list[str]
                   , prefix:str=None, step=400, sparql_api_url:str="https://query.wikidata.org/sparql"):
    """Execute a select query with a VALUES list which is too long to be executed all at once

    Args:
        values_list (list[str]): listof values to execute the query with
        unformatted_query (str): Unformatted SPARQL query. 
        Using the format method with as parameter the a part of the values list in string format must return the correctly formatted query.
        Example: SELECT ?p ?o WHERE {{ VALUES ?ex {{ {} }} ?ex ?p ?o }}
        return_keys (list[str]): The list of returned variable names of the query. In the previous example, ['p', 'o']
        prefix (str, optional): prefix of each element of the VALUES list. 
        If 'str', values are put in between quotation marks. Defaults to None.
        step (int, optional): Number of values to put into each run of the query. Defaults to 400.
        sparql_api_url (str, optional): API endpoint to send the query to. Defaults to "https://query.wikidata.org/sparql".

    Returns:
        list[dict]: Return the result of the query in list dict format. Each dict has all the key names of 'return_keys'
    """
    start_index = 0
    full_result = []
    while start_index < len(values_list):
        end_index = min(start_index+step, len(values_list))
        if prefix is None:
            query_values_str = ' '.join(values_list[start_index:end_index])
        elif prefix == 'str':
            query_values_str = '"'+'" "'.join(values_list[start_index:end_index])+'"'
        else:
            space_prefix = ' '+prefix
            query_values_str = prefix+space_prefix.join(values_list[start_index:end_index])
        
        query = unformatted_query.format(query_values_str)
        full_result += select_query(query, return_keys, sparql_api_url)
        start_index = end_index
    return full_result

def select_query(query:str, return_keys:list[str], sparql_api_url:str="https://query.wikidata.org/sparql")->list[dict]:
    """Send a SELECT query to an API endpoint and return the formatted result of the query

    Args:
        query (str): SPARQL SELECT query to execute
        return_keys (list[str]): The list of returned variable names of the query (ex: SELECT ?o ?p --> ['o', 'p'])
        sparql_api_url (str, optional): API endpoint to send the query to. Defaults to "https://query.wikidata.org/sparql".

    Returns:
        list[dict]: Return the result of the query in list dict format. Each dict has all the key names of 'return_keys'
    """
    sparql = SPARQLWrapper(sparql_api_url)
    sparql.setReturnFormat(JSON)
    sparql.setQuery(query)
    result = sparql.query().convert()['results']['bindings']
    mapped_result = []
    for r in result:
            r_dict = {}
            for key in return_keys:
                r_dict[key] = r[key]['value']
            mapped_result.append(r_dict)
    return mapped_result

def ask_query(query:str, sparql_api_url:str="https://query.wikidata.org/sparql")->bool:
    """Send an ASK query to an API endpoint and return the result   

    Args:
        query (str): SPARQL ASK query to execute
        sparql_api_url (str, optional): API endpoint to send the query to. Defaults to "https://query.wikidata.org/sparql".

    Returns:
        bool: Result of the query
    """
    sparql = SPARQLWrapper(sparql_api_url)
    sparql.setReturnFormat(JSON)
    sparql.setQuery(query)
    return sparql.query().convert()['boolean']
