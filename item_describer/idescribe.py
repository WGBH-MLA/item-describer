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

def form_system_prompt ():
    """
    Formulate the system prompt.
    (For now, this returns a fixed string.)
    """

    system_prompt = """
You are an audiovisual archivist creating item-level descriptions for the American Archive of Public Broadcasting.
You are sharp and analytical.
You provide a short description according to the user's request.
You do not add any commentary, explanation, or elaboration.
Your output must consist ONLY of the description the user has requested.
"""
    return system_prompt


def form_user_prompt( metadata, transcript ):
    """
    Formulate the user prompt from metadata and the transcript.
    """

    p = ""
    instr =  "Please write a short description of this item.  "
    instr += "Begin by saying what kind of item it is (mentioning radio or television and the genre, if known), what series (if any) it is from, and the year (if available).  "
    instr += "(But do not state the episode or program title.)\n\n"
    instr += "Then, with just two or three sentences, say what are the main topics, issues, and events discussed.  "
    instr += "After that, with just one more sentence, list other topics discussed.  "
    instr += "Beyond that basic info, please do not elaborate further.\n\n"

    metadata = json.dumps(metadata, indent=2)
    
    p += instr
    p += "Here is the metadata we currently have about this item:\n\n"
    p += "```\n"
    p += metadata
    p += "\n```\n\n"
    p += "Here is an automatically generated transcript.  Beware that this transcript may contain errors and misspellings.\n\n"
    p += '"""\n'
    p += transcript
    p += '\n\n"""\n'

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
    
    raw_metadata = get_raw_metadata( args.aapbid )
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
                                         max_tokens = 200 )
        print()
        print(description)
        print()
    

if __name__ == "__main__":
    main()
