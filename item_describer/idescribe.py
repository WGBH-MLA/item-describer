"""
idescribe.py

Takes an AAPB ID as input.
Collects current metadata and transcript.
Builds that data into a prompt for an LLM.
Uses that data to generate a description.
Writes the description to stdout

"""
import argparse
import json
import io

import requests

import pbcore_scullery as pb
import gbh_ai_helper as ai

from . import prompt_content as pc


def form_system_prompt ():
    """
    Formulate the system prompt.
    (For now, this returns a fixed string.)
    """
    system_prompt = pc.system_prompt

    return system_prompt


def form_user_prompt( metadata, transcript ):
    """
    Formulate the user prompt from metadata and the transcript.
    """

    metadata = json.dumps(metadata, indent=2)

    p = pc.user_prompt_instr
    p += "\n"
    p += pc.metadata_intro
    p += "\n```\n"
    p += metadata
    p += "\n```\n"
    p += pc.transcript_intro
    p += '\n"""\n'
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


def massage_metadata( asst:dict ) -> dict:

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


def aajson2txt( jstr:str ) -> str:

    td = json.loads(jstr)
    tt = ""
    for part in td["parts"]:
        tt += part["text"] + "\n"
    
    return tt


def get_transcript( url:str ) -> str:

    # get the transcript JSON
    response = requests.get(url)

    if url.find(".json") == -1:
        text = response.content
    else:
        text = aajson2txt(response.content)

    return text


def idescribe( aapbid:str, max_tokens=200 ) -> str:
    """
    Takes an AAPB ID as input. 
    Returns a short description of the item.
    Description is based on the current metadata and the transcript.
    """

    raw_metadata = get_raw_metadata( aapbid )
    metadata = massage_metadata( raw_metadata )

    transcript_url = raw_metadata.get("transcript_url","")

    if not transcript_url.strip():
        print("\nNO TRANSCRIPT AVAILABLE.\nWILL NOT ATTEMPT DESCRIPTION.\n")
    
    else:
        transcript_text = get_transcript( transcript_url )
        user_prompt = form_user_prompt( metadata, transcript_text )
        system_prompt = form_system_prompt()

        description = ai.one_completion( user_prompt,
                                         system_prompt,
                                         max_tokens=max_tokens )
    return description


def main():

    parser = parser = argparse.ArgumentParser(
        prog='idescribe',
        description='Creates a description for an AAPB ID',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("aapbid", metavar="ID",
        help="The AAPB ID for the item you wish to describe.")

    args = parser.parse_args()

    # check for valid identifier
    # To do: Add validation
    if not args.aapbid:
        pass

    description = idescribe(args.aapbid)

    print()
    print(description)
    print()
    

if __name__ == "__main__":
    main()
