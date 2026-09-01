"""
idescribe.py

Takes an AAPB ID as input.
Collects current metadata and transcript.
Builds that data into a prompt for an LLM.
Uses that data to generate a description.
Writes the description to stdout

"""
import argparse
import copy
import io
import os
import sys
from typing import Optional

import requests

import pbcore_scullery as pb
import gbh_ai_helper as ai

from . import __version__
from . import reformat 
from .prompt_content import pc


# Global prompt data structure
# (Can be changed by functions below.)
PC = copy.deepcopy(pc)

MAX_TOKENS_DEFAULT = 200
DEFAULT_TEMPERATURE = 0.2
DEFAULT_HTTP_TIMEOUT = 30

#DEFAULT_DEPLOYMENT = ai.get_default_azure_deployment()

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
                      dtype:str="description",
                      use_metadata:bool=True ):
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

    if use_metadata:
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
    try:
        response = requests.get(pbcore_url, timeout=DEFAULT_HTTP_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch PBCore metadata for AAPB ID '{aapbid}': {e}") from e

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
    try:
        response = requests.get(url, timeout=DEFAULT_HTTP_TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch transcript from '{url}': {e}") from e

    if url.find(".json") == -1:
        text = response.text.strip()
    else:
        text = reformat.aajson2txt(response.text)

    return text


def validate_output( raw:str,
                     dtype:str ) -> Optional[str]:

    if not raw:
        return None

    raw_clean = raw.strip()
    if not raw_clean or raw_clean.lower() == 'none':
        return None

    if PC[dtype]["options"]:
        out_list = [ t.strip() for t in raw_clean.split('\n') if t.strip() ]
        if not out_list:
            return None
        for t in out_list:
            if t not in PC[dtype]["options"]:
                return None
        return "\n".join(out_list)
    else:
        return raw_clean
        


def idescribe( aapbid:str, 
               dtype:str = "description",
               use_metadata:bool = True,
               max_tokens:int = MAX_TOKENS_DEFAULT,
               temperature:float = DEFAULT_TEMPERATURE,
               provider:str = None,
               model_ref:str = None ) -> dict:
    """
    Calls an LLM to generate descriptive metadata for an AAPB item, based
    on the current metadata and the transcript.

    As input, takes an AAPB ID. 

    Returns a dictionary as output
    """
    
    raw_metadata = get_raw_metadata( aapbid )

    if not raw_metadata:
        raise ValueError(
            f"COULD NOT GET ITEM-LEVEL METADATA FOR AAPB ID: {aapbid}. "
            "WILL NOT ATTEMPT DESCRIPTION."
        )

    metadata = massage_metadata( raw_metadata, dtype )
    metadata_str = reformat.format_metadata( metadata )

    transcript_url = raw_metadata.get("transcript_url","")

    if not transcript_url.strip():
        raise ValueError(
            f"NO TRANSCRIPT AVAILABLE FOR AAPB ID: {aapbid}. "
            "WILL NOT ATTEMPT DESCRIPTION."
        )

    else:
        transcript_text = get_transcript( transcript_url )

        user_prompt = form_user_prompt( metadata_str, 
                                        transcript_text, 
                                        dtype,
                                        use_metadata=use_metadata )
        
        system_prompt = form_system_prompt( dtype )

        # make the call to the model
        raw_output = ai.one_completion( user_prompt,
                                        system_prompt,
                                        max_tokens=max_tokens,
                                        temperature=temperature,
                                        provider=provider,
                                        model_ref=model_ref )        

        valid_output = validate_output( raw_output, dtype )

    output = {
        "valid_output": valid_output, 
        "raw_output": raw_output,
        "model_id": ai.get_source_model(provider, model_ref),
        "metadata_used": metadata_str,
        "transcript_url": transcript_url,
        "prompt_components": PC[dtype].copy()
    }

    return output


def main():

    global PC

    app_desc = f"AAPB Item Describer (version {__version__})\n"
    app_desc += "Generates descriptive metadata for an AAPB item using an LLM.\n\n"
    app_desc += f"Available LLM providers: {', '.join(ai.AVAILABLE_PROVIDERS)}\n"
    app_desc += f"Default LLM provider: {ai.DEFAULT_PROVIDER}\n"
    app_desc += f"Default Azure deployment: {ai.DEFAULT_AZURE_DEPLOYMENT}\n"
    app_desc += f"Default Bedrock model: {ai.DEFAULT_BEDROCK_MODEL}\n"
    #app_desc += f"Default LLM deployment alias: {ai.DEFAULT_DEPLOYMENT_ALIAS}\n"
    #app_desc += f"Default LLM deployment name:  {os.getenv(ai.DEFAULT_DEPLOYMENT_ALIAS)}\n"

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
    parser.add_argument("-x", "--ignore-metadata", action="store_true",
        help="Do not include existing metadata in the user prompt.")
    parser.add_argument("-t", "--type", metavar="TYPE", nargs="?", default="description",
        help="The type of descriptive metadata you want: 'description' or 'topics'")
    parser.add_argument("-s", "--custom-system-prompt", metavar="SYS", nargs="?", default=None,
        help="The file path to a text file with a custom system prompt")
    parser.add_argument("-i", "--custom-instruction", metavar="INSTR", nargs="?", default=None,
        help="The file path to a text file with custom instructions for the prompt")
    parser.add_argument("-z", "--max-tokens", metavar="MAX", nargs="?", default=MAX_TOKENS_DEFAULT,
        help="The maximum number of tokens the LLM should produce as its output")
    parser.add_argument("-p", "--provider", metavar="PROVIDER", nargs="?", default=ai.DEFAULT_PROVIDER,
        help="The provider of the model and API you wish to use")        
    parser.add_argument("-m", "--model-ref", metavar="MODEL", nargs="?", default=None,
        help="The name of the Azure model deployment or Bedrock model you wish to use.  (If omitted defaults to the provider default.)")        

    args = parser.parse_args()

    # check for valid identifier
    # To do: Add validation
    if args.aapbid and args.aapbid.strip():
        aapbid = args.aapbid.strip()
    else:
        print("Error: An AAPB ID must be provided.")
        return 1

    if args.type:
        if args.type in ["description", "topics"]:
            dtype = args.type
        else:
            print("\nWarning: Invalid type specified.  Run with `-h` for help.")
            dtype = "description"
    else:
        dtype = "description"

    if args.custom_system_prompt:
        if os.path.isfile(args.custom_system_prompt):
            with open(args.custom_system_prompt) as f:
                PC[dtype]["system_prompt"] = f.read()
        else:
            print("\nWarning: Invalid path to custom system prompt.  Will use default system prompt.")

    if args.custom_instruction:
        if os.path.isfile(args.custom_instruction):
            with open(args.custom_instruction) as f:
                PC[dtype]["user_prompt_instr"] = f.read()
        else:
            print("\nWarning: Invalid path to custom instructions.  Will use default instructions.")

    if args.max_tokens:
        try:
            max_tokens = int(args.max_tokens)
        except ValueError as e:
            print("\nWarning: Invalid value for max tokens.")
            print(f"  ValueError: {e}")
            print(f"Will use default value of {MAX_TOKENS_DEFAULT}.")
            max_tokens = MAX_TOKENS_DEFAULT
    
    temperature = DEFAULT_TEMPERATURE

    provider = args.provider.strip().lower()

    if args.model_ref:
        model_ref = args.model_ref.strip()
    else:
        if provider == "azure":
            model_ref = ai.DEFAULT_AZURE_DEPLOYMENT
        elif provider == "bedrock":
            model_ref = ai.DEFAULT_BEDROCK_MODEL
        else:
            print(f"Unknown provider '{provider}'. Supported providers: {', '.join(ai.AVAILABLE_PROVIDERS)}.")
            return 1

    # run the item describer function
    try: 
        output = idescribe( aapbid, 
                            dtype, 
                            use_metadata = not(args.ignore_metadata),
                            max_tokens=max_tokens,
                            temperature=temperature,
                            provider=provider,
                            model_ref=model_ref ) 
    except (ValueError, RuntimeError) as e:
        print(e)
        return 1

    # write output to stdout
    print()

    # verbose output
    if args.verbose:
        print("# ITEM DESCRIBER RUN INFO")
        print()
        print(f"* AAPB ID: {aapbid}")
        print(f"* Model API provider:       {provider}")
        print(f"* User-specified model ref: {model_ref}")
        print(f"* Canonical model ID:       {output['model_id']}")
        print(f"* Output metadata type:     {dtype}")
        print(f"* Maximum output tokens:    {max_tokens}")
        print(f"* Model temperature:        {temperature}")
        print()
        print(f"# PROMPT COMPONENTS")
        for k in ["system_prompt", "user_prompt_instr", "options", "metadata_intro", "transcript_intro"]:
            print(f"\n## {k}:")
            print(str(PC[dtype][k]).strip())

        print("\n## Current metadata used:")
        print(output['metadata_used'])
        print("\n## Transcript used:")
        print(output['transcript_url'])
        print()
        print("# ITEM DESCRIBER RUN OUTPUT")
        print()

    # substantive output
    if output["valid_output"]:
        print(output["valid_output"])
    elif output["raw_output"]:
        print("MODEL DID NOT PRODUCE VALID OUTPUT.")
        print("RAW MODEL OUTPUT:\n")
        print(output["raw_output"])
    else:
        print("MODEL PRODUCED NO OUTPUT.")
    print()

    return 0

if __name__ == "__main__":
    sys.exit(main())
