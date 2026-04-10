"""
prompt_content.py

Define strings that supply the content of prompts to item describer.

All data is organized into a dictionary at the top level of this module.

To use this module, import that `pc` dictionary.

"""


# top level dicionary
pc = {}

#
# General purpose text
#
general_metadata_intro = """
Here is the metadata we currently have about this item:
"""
general_transcript_intro = """
Here is an automatically generated transcript.  Beware that this transcript may contain errors and misspellings.
"""
general_system_prompt = """
You are cataloging archivist for the American Archive of Public Broadcasting.
You are sharp and analytical.
You provide concise output according to the user's request.
You do not add any commentary, explanation, or elaboration.
Your output must consist ONLY of the description the user has requested.
"""

############################################################################
#
# Prompts for generating descriptions
#
pc["description"] = {}

pc["description"]["system_prompt"] = general_system_prompt

pc["description"]["user_prompt_instr"] = """
Please write a short description of this item.  
In the first sentence, say what kind of item it is (mentioning radio or television and the genre, if known), what series (if any) it is from, and the year (if available).  (But do not state the episode or program title.)
Then, after skipping a line, in the second sentence, say what are the main topics, issues, and events discussed. 
Optionally, skip a line and add a third sentence, listing any other topics discussed.  
Beyond that basic description, please do not elaborate further.
"""
pc["description"]["options_intro"] = None
pc["description"]["options"] = None
pc["description"]["metadata_intro"] = general_metadata_intro
pc["description"]["transcript_intro"] = general_transcript_intro


############################################################################
#
# Prompts for generating topics
#
from .topics_options import topics_options_str
from .reformat import format_options

pc["topics"] = {}

pc["topics"]["system_prompt"] = general_system_prompt
pc["topics"]["user_prompt_instr"] = """
Describe this item with one or more topics from list below.
You may choose no more than three topics.
Without any introduction or explanation, output the topics you selected in a comma-separated list.
If cannot assign topics to the item, simply output "NONE" and nothing else.
"""
pc["topics"]["options_intro"] = """
Here is a list of topics from which you may select:
"""
pc["topics"]["options"] = format_options(topics_options_str)
pc["topics"]["metadata_intro"] = general_metadata_intro
pc["topics"]["transcript_intro"] = general_transcript_intro

############################################################################

