import json
from pubmed_client import get_publication_info

async def handle_fun_call(fun_name: str, params: str):
    retval = ''
    if fun_name == 'get_publication_info':
        param_dict = json.loads(params)
        pub_ids = param_dict['pubids'].split(',')
        retval = json.dumps(await get_publication_info(pub_ids, param_dict['request_id']))
    else:
        print(f"WARNING: did not recognize #{fun_name} as a valid tool to call")

    return retval
