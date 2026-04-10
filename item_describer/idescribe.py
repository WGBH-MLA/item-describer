"""
idescribe.py

Takes an AAPB ID as input.
Collects current metadata and transcript.
Builds that data into a prompt for an LLM.
Uses that data to generate a description.
Writes the description to stdout

"""
import argparse
import io

import requests

import pbcore_scullery as pb
import gbh_ai_helper as ai

from . import reformat 
from .prompt_content import pc


def form_system_prompt ( dtype:str="description" ):
    """
    Formulate the system prompt.
    (For now, this returns a fixed string.)
    """
    system_prompt = pc[dtype]["system_prompt"].strip()

    return system_prompt


def form_user_prompt( metadata:str, 
                      transcript:str,
                      dtype:str="description" ):
    """
    Formulate the user prompt from metadata and the transcript.
    """

    p = ""

    p += pc[dtype]["user_prompt_instr"].strip()
    p += "\n\n"

    if pc[dtype]["options"]:
        p += pc[dtype]["options_intro"].strip()
        p += "\n"
        p += pc[dtype]["options_str"].strip()
        p += "\n\n"

    p += pc[dtype]["metadata_intro"].strip()
    p += "\n```\n"
    p += metadata
    p += "\n```\n\n"
    p += pc[dtype]["transcript_intro"].strip()
    p += '\n\n"""\n'
    p += transcript
    p += '\n"""\n'

    return p


def get_raw_metadata( aapbid:str ) -> dict:

    pbcore_url = "https://americanarchive.org/catalog/"
    pbcore_url += aapbid.strip()
    pbcore_url += ".pbcore"

    # get the PBCore XML file
    response = requests.get(pbcore_url)

    # create a filepath like object for it
    fio = io.BytesIO(response.content)

    # extract dictionary of important fields and values
    assttbl, _ = pb.framify.tablify( [fio] )

    return assttbl[0]


def massage_metadata( asst:dict, dtype="description" ) -> dict:

    asst["item_duration"] = asst.get("proxy_duration","")
    asst["item_date"] = asst.get("single_date","")
    
    keep_if_nonempty = [ 
        "media_type",
        "asset_type",
        "item_date",
        "series_title",
        "program_title",
        "episode_title",
        "segment_title",
        "raw_footage_title",
        "promo_title",
        "clip_title",
        "series_description",
        "program_description",
        "episode_description",
        "segment_description",
        "raw_footage_description",
        "promo_description",
        "clip_description",
        "producing_organization",
        "item_duration" ]
    
    keep_always = [
        "series_title" ]

    m = { k: v for k, v in asst.items() 
            if  k in keep_always or 
            (k in keep_if_nonempty and asst[k] ) }

    return m


def get_transcript( url:str ) -> str:

    # get the transcript JSON
    response = requests.get(url)

    if url.find(".json") == -1:
        text = response.text.strip()
    else:
        text = reformat.aajson2txt(response.text)

    return text


def validate_output( raw:str,
                     dtype:str ) -> (str,str):

    if raw.strip().lower() == 'none':
        valid_output = None
    elif pc[dtype]["options"]:
        valid_output = raw.strip()
        out_list = [ t.strip() for t in raw.strip().split('\n') ]
        for t in out_list:
            if t not in pc[dtype]["options"]:
                valid_output = None
    else:
        valid_output = raw.strip()
    
    return valid_output
        


def idescribe( aapbid:str, 
               dtype:str = "description",
               verbose:bool = False,
               max_tokens:int = 200 ) -> str:
    """
    Calls an LLM to generate descriptive metadata for an AAPB item, based
    on the current metadata and the transcript.
    Takes an AAPB ID as input. 
    Returns an order pair as output.
    First item is validated output, which will be `None` if LLM ouput was 
    not valid.
    Second item is the raw LLM output.
    """

    raw_metadata = get_raw_metadata( aapbid )
    metadata = massage_metadata( raw_metadata, dtype )
    metadata_str = reformat.format_metadata( metadata )

    transcript_url = raw_metadata.get("transcript_url","")

    if verbose:
        print(f"\nAAPB ID: {aapbid}")
        print("\nCurrent metadata used:")
        print(metadata_str)
        print("\nTranscript used:")
        print(transcript_url)
        print("\nOUTPUT:")

    if not transcript_url.strip():
        print("\nNO TRANSCRIPT AVAILABLE.  WILL NOT ATTEMPT DESCRIPTION.\n")
        valid_output = raw_output = None
    else:
        transcript_text = get_transcript( transcript_url )
        user_prompt = form_user_prompt( metadata_str, transcript_text, dtype )
        system_prompt = form_system_prompt( dtype )

        raw_output = ai.one_completion( user_prompt,
                                        system_prompt,
                                        max_tokens=max_tokens )
        valid_output = validate_output( raw_output, dtype )

    return valid_output, raw_output



def main():

    parser = parser = argparse.ArgumentParser(
        prog='idescribe',
        description='Generates descirptive metadata for an AAPB item using an LLM.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("aapbid", metavar="ID",
        help="The AAPB ID for the item you wish to describe.")
    parser.add_argument("-t", "--type", metavar="TYPE", nargs="?", default="description",
        help="The type of descriptive metadata you want: 'description' or 'topics'")
    parser.add_argument("-v", "--verbose", action="store_true",
        help="Produce verbose/diagnostic output.")

    args = parser.parse_args()

    # check for valid identifier
    # To do: Add validation
    if args.aapbid:
        aapbid = args.aapbid
    else:
        return None

    if args.type:
        if args.type in ["description", "topics"]:
            dtype = args.type
        else:
            print("Warning: Invalid type specified.  Run with `-h` for help.")
            dtype = "desription"
    else:
        dtype = "desription"

    valid_output, raw_output = idescribe(aapbid, dtype, verbose=args.verbose)

    if valid_output:
        print()
        print(valid_output)
    elif raw_output:
        print("INVALID MODEL OUTPUT:")
        print(raw_output)
    else:
        print("NO OUTPUT.")
    print()
    

if __name__ == "__main__":
    main()
