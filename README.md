# capstone-legal-docker-scraper
This repo contains the `dockerfile` and the scraper.py for the ETL pipeline located at : https://github.com/hxwwong/capstone-legal

The output will be a parquet file, `cases.parquet` containing case information about the jurisprudence scraped from CDAsia-Online (https://cdasiaonline-com.dlsu.idm.oclc.org/), a prominent legal database. After scraping, it will upload `cases.parquet` to the specified GCS bucket.

Accessing the website and uploading to GCS will require credentials that have been stored in a .env file that has been omitted from this repo.

Note: Since the docker-operator is an entirely independent process from the rest of the capstone-legal dag, any modifications to the end output, including any processes with extraction, validation, transformation, and loading will need to be made using the contents of this repo. The outputs will then be built into a docker image, and pushed. 

The `DockerOperator` in `capstone-legal/dags/scraper_dag.py` will then pull the latest version of the built image specified in the operator's base arguments. 

# Setup 
In order to create your own versoin of the docker image, you can run the following commands in the directory containing the relevant files: 

  1. Build the image in the current directory:
  `docker build -t <image name> .`

  2. To test the image on your local machine: 
  `docker run --env-file <env file name> <image name>` 

  3. To push the image into your dockerhub repo, which will be pulled by the DockerOperator in the `scraper_dag.py` in `capstone-legal/dags`: 
  `docker push` 
  
# Modifying scraper.py & Troubleshooting 
`scraper.py` is a standalone ETL process that scrapes CDAasia Online, a paywalled legal database, runs spacy, wordcount, and NER transformations, and loads the resulting parquet file into the Google Cloud Storage Bucket. 

## Credentials & .env files 
The code itself relies on having a `develop.env` file which should be part of the repo **before it is built and pushed** to supply the credentials via `os.environ('CREDENTIAL'`) in the `gcs_upload_file` function.

## Scraping CDAsia-Online 
The scraper is designed to scrape the version of the cases in the target file, and in the first page to access the latest uploads. Once it goes to the target URL, it scrapes all the available information in the summary page, and then navigates to each individual case and then saves the content of the document.  

Note that it is possible to receive errors in the code due to server-side issues. This is most common with errors that indicate a specific class or selector element is missing (e.g. `No such class element 'doc-inv-c'`) can likely be resolved by re-running the script or the DAG it is associated with.

## Data Transformation with `word_count()` and `NER()`

The transformation uses a series of for-loops and dictionaries to calculate the frequency of each word, and Named Entity 
It's especially important to note that to generate parquet files, you need to make sure that the dataframes are string objects, and not dicts. A common problem was that the parquets were modified at every step (during the word_count and NER functions) due to certain columns being labeled as dictionaries. This can be addressed by affixing `.astype('str')` method at the end of every transformation. 

## Loading 
The data is loaded to the Google Cloud Storage bucket in parquet form using the credentials. Following this, the container exits, and all of its contents are wiped. Since nothing is saved locally, this step is essential to seeing the output. 

# Troubleshooting, Challenges, and Future Improvements
Sometimes, when pushing an image to airflow, it might be necessary to re-compose the capstone-legal project by running `docker compose down` and `docker compose up` in the directory. This ensures the cache is cleared, and the updated image is pulled. 

A challenge noted is the amount of time it took to build images, run them, and push them online. The need to constantly recompose images and make sure everything was up to date made the workflow challenging and prone to bugs/simple errors. 

Additionally, it was difficult to debug since the process of making the system run relied on creating a selenium process that didn't have GUI, and wouldn't cause trouble when deployed on the Google Compute Engine's VM. Often, the frequent builds and pushes would consume large amounts of memory after repeated tests, to the point that a new VM with more disk space needed to be instantiated. 

Future improvements can include: 
1) Creating a more robust data validation system. The current method primarily uses pandas due to limitations in time for the project's development. 
2) Additionally, there are frequent errors that can occur when the server-side of the website fails. Having more try-except clauses, and ways to handle server side errors could help make this proccess smoother and easier to track/debug.
