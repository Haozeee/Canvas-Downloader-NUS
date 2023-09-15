# Canvas Downloader

Automatically downloads files from Canvas and stores them locally with the same directory strucutre as it is stored in Canvas. 
You no longer need to manually download and organise your module's files. 
Just run the Python script and it will download any new files that the Course instructor has uploaded that does not currently exisit on your local directory.

## Steps
- Login to Canvas and go to Account -> Settings. Generate an access token there.
- Head to the `config.yml` file and add the created token there.
- In the same config file, set the base directory from which all the files should be stored at.
