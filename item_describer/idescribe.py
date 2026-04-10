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
        p += pc[dtype]["options"].strip()
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
    
    to_keep = [ "media_type",
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

    m = { k: v for k, v in asst.items() if ( k in to_keep and asst[k] ) }

    return m


def get_transcript( url:str ) -> str:

    # get the transcript JSON
    response = requests.get(url)

    if url.find(".json") == -1:
        text = response.content.strip()
    else:
        text = reformat.aajson2txt(response.content)

    return text


def idescribe( aapbid:str, 
               dtype:str="description",
               max_tokens:int=200 ) -> str:
    """
    Takes an AAPB ID as input. 
    Returns a short description of the item.
    Description is based on the current metadata and the transcript.
    """

    raw_metadata = get_raw_metadata( aapbid )
    metadata = massage_metadata( raw_metadata, dtype )
    metadata_str = reformat.format_metadata( metadata )

    transcript_url = raw_metadata.get("transcript_url","")

    if not transcript_url.strip():
        print("\nNO TRANSCRIPT AVAILABLE.\nWILL NOT ATTEMPT DESCRIPTION.\n")
        description = ""
    else:
        transcript_text = get_transcript( transcript_url )
        user_prompt = form_user_prompt( metadata_str, transcript_text, dtype )
        system_prompt = form_system_prompt( dtype )

        output = ai.one_completion( user_prompt,
                                    system_prompt,
                                    max_tokens=max_tokens )
    return output



def main():

    parser = parser = argparse.ArgumentParser(
        prog='idescribe',
        description='Generates descirptive metadata for an AAPB item',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("aapbid", metavar="ID",
        help="The AAPB ID for the item you wish to describe.")
    parser.add_argument("-t", "--type", metavar="TYPE", nargs="?", default="description",
        help="The type of metadata you want: 'description' or 'topics'")

    args = parser.parse_args()

    # check for valid identifier
    # To do: Add validation
    if not args.aapbid:
        pass

    if args.type:
        if args.type in ["description", "topics"]:
            dtype = args.type
        else:
            print("Warning: Invalid type specified.  Run with `-h` for help.")
            dtype = "desription"
    else:
        dtype = "desription"

    description = idescribe(args.aapbid, dtype)

    print()
    print(description)
    print()
    

if __name__ == "__main__":
    main()
