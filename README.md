# nismod-api-extract
Allows data to be extracted from NISMOD-API with a number of options built-in to automate the process.

## usage
It has been developed to run using docker.

To build with docker:
 `docker build . -t extract-nismod`

To run with docker (after building). A number of options need to be passed to extract the data required.
 `docker run -v <local path>/output:/data/outputs -t extract-nismod`

* api username & password
  * `--env username=<username>`
  * `--env password=<password>`
* feature layer - developed with modelling in mind, and thus supports three feature layers currently: 'developed-land', 'water-bodies' and 'buildings'
  * `--env feature_layer=<layer type>` 
* area codes - the tool supports data selection using OAs, LADs or GORs
  * `--env area_codes=<text string of area codes>`
  * `--env scale=<the type of area codes passed (lads, gors or oas)>`
* output_name - the name to be given to the output file generated. if not passed, name will use the feature layer
  * `--env output_name=<the name for the output file>`
