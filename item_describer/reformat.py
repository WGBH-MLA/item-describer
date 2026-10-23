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


def format_options( options_list:list ) -> str:
    """
    Reformats a list of options.
    Takes a list of options.
    Returns a formatted list of options.
    """
    options_str = ""
    for t in options_list:
        options_str += f'* {t}\n'
    return options_str


def shuffle_list( orig:list ) -> list:
    """
    Simple, deterministic list shuffling, ensuring significantly
    different position in list for each item.
    """
    opts = orig.copy()
    opts = swap_adjacents(opts)
    opts = cut_deck(opts)
    return opts

def swap_adjacents( orig:list ) -> list:
    opts = orig.copy()
    p = (0, 1)
    while p[1] < len(opts):
        a = opts[p[0]]
        opts[p[0]] = opts[p[1]]
        opts[p[1]] = a
        p = (p[0]+2, p[1]+2)
    return opts

def cut_deck( orig:list ) -> list:
    opts = orig.copy()
    cut_idx = len(opts) // 2
    opts = opts[cut_idx:] + opts[0:cut_idx]
    return opts