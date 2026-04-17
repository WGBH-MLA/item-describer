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
import os
import importlib.metadata

import requests

import pbcore_scullery as pb
import gbh_ai_helper as ai

from . import reformat 
from .prompt_content import pc

# get version number from `pyproject.toml` file
__version__ = importlib.metadata.version("item-describer")


# Global prompt data structure
# (Can be changed by functions below.)
PC = pc.copy()

MAX_TOKENS_DEFAULT = 200

############################################################################

def form_system_prompt ( dtype:str="description" ):
    """
    Formulate the system prompt.
    (For now, this returns a fixed string.)
    """

    system_prompt = PC[dtype]["system_prompt"].strip()

    return system_prompt


def form_user_prompt( metadata:str, 
                      transcript:str,
                      dtype:str="description" ):
    """
    Formulate the user prompt from metadata and the transcript.
    """

    p = ""

    p += PC[dtype]["user_prompt_instr"].strip()

    p += "\n\n"

    if PC[dtype]["options"]:
        p += PC[dtype]["options_intro"].strip()
        p += "\n"
        p += PC[dtype]["options_str"].strip()
        p += "\n\n"

    p += PC[dtype]["metadata_intro"].strip()
    p += "\n```\n"
    p += metadata
    p += "\n```\n\n"
    p += PC[dtype]["transcript_intro"].strip()
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
    asstdict, _ = pb.framify.dictify( fio )

    return asstdict


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
    elif PC[dtype]["options"]:
        valid_output = raw.strip()
        out_list = [ t.strip() for t in raw.strip().split('\n') ]
        for t in out_list:
            if t not in PC[dtype]["options"]:
                valid_output = None
    else:
        valid_output = raw.strip()
    
    return valid_output
        


def idescribe( aapbid:str, 
               dtype:str = "description",
               verbose:bool = False,
               max_tokens:int = MAX_TOKENS_DEFAULT,
               deployment_alias = ai.DEFAULT_DEPLOYMENT_ALIAS ) -> str:
    """
    Calls an LLM to generate descriptive metadata for an AAPB item, based
    on the current metadata and the transcript.
    Takes an AAPB ID as input. 
    Returns an order pair as output.
    First item is validated output, which will be `None` if LLM ouput was 
    not valid.
    Second item is the raw LLM output.
    """

    if verbose:
        print(f"\n* Model deployment alias: {deployment_alias}")
        print(f"* Model deployment name: {os.getenv(deployment_alias)}")
        print(f"\n* Ouput metadata type: '{dtype}'")
        print(f"* Maximum output tokens: {max_tokens}")
        print()

    raw_metadata = get_raw_metadata( aapbid )

    if not raw_metadata:
        print(f"\nCOULD NOT GET ITEM-LEVEL METADATA FOR AAPB ID: {aapbid}")
        print("\nWILL NOT ATTEMPT DESCRIPTION.\n")
        valid_output = raw_output = None
        return valid_output, raw_output

    metadata = massage_metadata( raw_metadata, dtype )
    metadata_str = reformat.format_metadata( metadata )

    transcript_url = raw_metadata.get("transcript_url","")

    if verbose:
        print(f"* PROMPT COMPONENTS: ")
        for k in ["system_prompt", "user_prompt_instr", "options", "metadata_intro", "transcript_intro"]:
            print(f"\n* {k}:")
            print(str(PC[dtype][k]).strip())
        print(f"\n* AAPB ID: {aapbid}")
        print("\n* Current metadata used:")
        print(metadata_str)
        print("\n* Transcript used:")
        print(transcript_url)

    if not transcript_url.strip():
        print("\nNO TRANSCRIPT AVAILABLE.")
        print("\nWILL NOT ATTEMPT DESCRIPTION.\n")
        valid_output = raw_output = None
        return valid_output, raw_output

    else:
        transcript_text = get_transcript( transcript_url )

        user_prompt = form_user_prompt( metadata_str, 
                                        transcript_text, 
                                        dtype )
        
        system_prompt = form_system_prompt( dtype )

        raw_output = ai.one_completion( user_prompt,
                                        system_prompt,
                                        max_tokens=max_tokens,
                                        deployment_alias=deployment_alias )
        
        valid_output = validate_output( raw_output, dtype )


    return valid_output, raw_output



def main():

    global PC

    app_desc = f"AAPB Item Describer (version {__version__})\n"
    app_desc += "Generates descriptive metadata for an AAPB item using an LLM.\n\n"
    app_desc += f"Default LLM deployment alias: {ai.DEFAULT_DEPLOYMENT_ALIAS}\n"
    app_desc += f"Default LLM deployment name:  {os.getenv(ai.DEFAULT_DEPLOYMENT_ALIAS)}\n"

    class CustomFormatter(argparse.RawDescriptionHelpFormatter, 
                          argparse.ArgumentDefaultsHelpFormatter):
        pass

    parser = argparse.ArgumentParser(
        prog='idescribe',
        description=app_desc,
        formatter_class=CustomFormatter
    )
    parser.add_argument("aapbid", metavar="ID",
        help="The AAPB ID for the item you wish to describe.")
    parser.add_argument("-v", "--verbose", action="store_true",
        help="Produce verbose/diagnostic output.")
    parser.add_argument("-t", "--type", metavar="TYPE", nargs="?", default="description",
        help="The type of descriptive metadata you want: 'description' or 'topics'")
    parser.add_argument("-s", "--custom-system-prompt", metavar="SYS", nargs="?", default=None,
        help="The file path to a text file with a custom system prompt")
    parser.add_argument("-i", "--custom-instruction", metavar="INSTR", nargs="?", default=None,
        help="The file path to a text file with custom instructions for the prompt")
    parser.add_argument("-m", "--max-tokens", metavar="MAX", nargs="?", default=MAX_TOKENS_DEFAULT,
        help="The maximum number of tokens the LLM should produce as its output")
    parser.add_argument("-d", "--deployment", metavar="DEPLOY", nargs="?", default=ai.DEFAULT_DEPLOYMENT_ALIAS,
        help="The ~/.gbhai alias of the model deployment you want to use")        

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
            dtype = "description"
    else:
        dtype = "description"

    if args.custom_system_prompt:
        if os.path.isfile(args.custom_system_prompt):
            with open(args.custom_system_prompt) as f:
                PC[dtype]["system_prompt"] = f.read()
        else:
            print("Warning: Invalid path to custom system prompt.  Will use default system prompt.")

    if args.custom_instruction:
        if os.path.isfile(args.custom_instruction):
            with open(args.custom_instruction) as f:
                PC[dtype]["user_prompt_instr"] = f.read()
        else:
            print("Warning: Invalid path to custom instructions.  Will use default instructions.")

    if args.max_tokens:
        try:
            max_tokens = int(args.max_tokens)
        except ValueError as e:
            print("Warning: Invalid value for max tokens.")
            print(f"  ValueError: {e}")
            print(f"Will use default value of {MAX_TOKENS_DEFAULT}.")
            max_tokens = MAX_TOKENS_DEFAULT

        
    deployment_alias = args.deployment
    deployment_name = os.getenv(deployment_alias)
    if not deployment_name:
        print("Warning:  Model deployment alias didn't correspond to a deployment name.")
        print(f"Will use default deployment alias: {ai.DEFAULT_DEPLOYMENT_ALIAS}")
        deployment_alias = ai.DEFAULT_DEPLOYMENT_ALIAS

    valid_output, raw_output = idescribe( aapbid, 
                                          dtype, 
                                          max_tokens=max_tokens,
                                          deployment_alias=deployment_alias,
                                          verbose=args.verbose)

    if args.verbose:
        print("\n*** OUTPUT APPEARS BELOW. ***")
        
    print()
    if valid_output:
        print(valid_output)
    elif raw_output:
        print("MODEL DID NOT PRODUCE VALID OUTPUT.")
        print("RAW MODEL OUTPUT:\n")
        print(raw_output)
    else:
        print("NO OUTPUT.")
    print()
    

if __name__ == "__main__":
    main()
