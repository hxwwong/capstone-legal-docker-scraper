from selenium import webdriver 
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.chrome.options import Options 
from selenium.webdriver.common.by import By 
from time import sleep 
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager 
import os 
import dotenv
import pandas as pd 
import boto3 
from google.cloud import bigquery, storage
from io import StringIO, BytesIO
import spacy


BUCKET_NAME = "capstone-legal"
MY_FOLDER_PREFIX = "hans-capstone"
DATA_PATH = "/app"

# loading the env files for website credentials 
# replace these with your own 
dotenv.load_dotenv('develop.env')

## INITIALIZING SELENIUM ## 

login_page = "https://login.dlsu.idm.oclc.org/login?qurl=https://cdasiaonline.com%2fl%2fee17a146%2fsearch%3fyear_end%3d2022%26year_start%3d2022"

# window setings 

options = webdriver.ChromeOptions() 
options.add_argument("--headless")
options.add_argument("--start-maximized") 
options.add_argument("--disable-notifications")
options.add_argument("--incognito")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
driver.get(login_page)
driver.maximize_window() 
sleep(3) 

# inputting credentials from the dotenv file 

#  find_element(by=By.NAME, value=name)
username = driver.find_element(by=By.NAME, value='user') 
username.send_keys(os.environ['CDA_UN'])
sleep(1)

password = driver.find_element(by=By.NAME, value='pass') 
password.send_keys(os.environ['CDA_PW'])
sleep(1)

submit_button = driver.find_element(by=By.NAME, value='login') 
submit_button.click()
sleep(3)

# clicking the prompt after being redirected from login_page 
continue_button = driver.find_element(by=By.CLASS_NAME, value='btn-card-submit')
continue_button.click()

#############
## SCRAPER ## 
############# 

# collecting all the rows containing cases entries
cases = driver.find_elements(by=By.CLASS_NAME, value='i-menu-newtab')
data_list = [] 

# finding  core elements within each case entry 
for case in cases: 
    td = case.find_elements(by=By.TAG_NAME, value='td')
    ref_num = td[0].text # reference number (eg G.R. 1234)
    case_name = td[1].text # eg (Person A v. Person B.)
    judge = td[2].text # eg (HERNANDEZ, J)
    date = td[4].text # eg 2022-03-21
    url = case.get_attribute('data-href') # https://cdasia-online...

    # storing info as a dict for dataframe 
    data = {'ref_num': ref_num, 
            'case': case_name, 
            'judge': judge, 
            'date':date, 
            'url':url} 

    data_list.append(data)

def scrape_cases(url): 
    driver.get(url)
    sleep(3)
    doc = driver.find_element(by=By.CLASS_NAME, value='doc-view-container')
    return doc.text.strip() 
    



def word_count(text):
    words = text.split() # needs handling for Nonetype objects 
   
    # filtering for words w/ special chars
    temp = []
    for word in words: 
        s = ""
        for c in word: 
            if((ord(c) >= 97 and ord(c) <= 122) or (ord(c) >= 65 and ord(c) <= 90)):
                s += c
        temp.append(s.lower())
    # filtering out words < 3 chars
    temp2 = []
    for word in temp: 
        if len(word) >= 3:
            temp2.append(word)
                
            
    freq = [temp2.count(w) for w in temp2]
    word_dict = dict(zip(temp2, freq))
    return word_dict
    
def ner(text):
    nlp = spacy.load("en_core_web_sm")  
    doc = nlp(text)
    # print("Noun phrases:", [chunk.text for chunk in doc.noun_chunks])
    # print("Verbs:", [token.lemma_ for token in doc if token.pos_ == "VERB"])
    ner = {}
    for entity in doc.ents:
        ner[entity.text] = entity.label_
        print(entity.text, entity.label_)
    return ner


# exporting to a dataframe & csv
df = pd.DataFrame(data_list)
df['body_text'] = df['url'].apply(lambda x: scrape_cases(x))
df['sum_word_cnt'] = df['body_text'].apply(lambda x: len(x.split()))
df['dict_word_cnt'] = df['body_text'].apply(lambda x: word_count(x)).astype('str')
df['NER'] = df['body_text'].apply(lambda x: ner(x)).astype('str')



df.to_parquet('cases.parquet')







print("successfully scraped")
print(os.listdir(DATA_PATH))





def upload_file_to_gcs(remote_file_name, local_file_name):
    gcs_client = boto3.client(
        "s3",
        region_name="auto",
        endpoint_url="https://storage.googleapis.com",
        aws_access_key_id=os.environ["SERVICE_ACCESS_KEY"],
        aws_secret_access_key=os.environ["SERVICE_SECRET"],
    )
    gcs_client.upload_file(local_file_name, BUCKET_NAME, remote_file_name)

upload_file_to_gcs(remote_file_name='cases.parquet', local_file_name='cases.parquet')
print("Successfully uploaded to GCP")