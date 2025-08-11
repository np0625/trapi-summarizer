import json
from pubmed_client import get_publication_info

async def handle_fun_call(fun_name: str, args=str):
    retval = ''
    if fun_name == 'get_publication_info':
        arg_dict = json.loads(args)
        pub_ids = arg_dict['pubids'].split(',')
        retval = json.dumps(await get_publication_info(pub_ids, arg_dict['request_id']))
    else:
        print(f"WARNING: did not recognize #{fun_name} as a valid tool to call")

    return retval
