# Item Describer

This is a Python package that uses an LLM to create a brief description of an item, based on the item's transcript and the currently available metadata.

## Setup

### Installation

This package depends on two other packages that you need to install first:
- The [PBCore Scullery](https://github.com/WGBH-MLA/pbcore_scullery)
- The [GBH AI Helper](https://github.com/WGBH-MLA/gbh-ai-helper)

Then install this package the same way you installed the above packages:  Clone the repository.  Change to the repository directory and do a `pip install .` to install the package and its dependencies.

(For developers, do `pip install -e .` to install in editable mode.)

### Credentials

For the package to be useful, you need info and secrets stored in a file in your home directory.  Call your file `~/.gbh_ai`.  It defines environment variables `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `OPENAI_API_VERSION`, `DEPLOY_GPT41MINI`.

An example template can be found in the `.gbh_ai.example` file in the [GBH AI Helper repo](https://github.com/WGBH-MLA/gbh-ai-helper)


## Usage

The package has only a single interaction mode.  Just enter the command `idescribe` with the AAPB ID as a single argument, for example:
```
$ idescribe cpb-aacip-37-51vdnmxn
```

