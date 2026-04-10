import json

def aajson2txt( jstr:str ) -> str:

    td = json.loads(jstr)
    tt = ""
    for part in td["parts"]:
        tt += part["text"] + "\n"
    
    return tt.strip()


def format_metadata( metadata:dict ) -> str:
    
    return json.dumps(metadata, indent=2).strip()


def list_options( raw:str ) -> list:

    raw = raw.strip()
    options_list = raw.split("\n")
    options_list = [ t.strip() for t in options_list if t.strip() ]
    return options_list


def format_options( raw:str ) -> str:
    """
    Reformats a list of options.
    Takes a string with one item per line.
    Returns a formatted list of options.
    """
    options_list = list_options( raw ) 
    options_str = ""
    for t in options_list:
        options_str += f'* {t}\n'
    return options_str
