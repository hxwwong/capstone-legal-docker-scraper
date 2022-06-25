FROM selenium/standalone-chrome

USER root

WORKDIR /app

RUN wget https://bootstrap.pypa.io/get-pip.py
RUN apt-get update -y && apt-get install -y python3-distutils
RUN python3 get-pip.py
ADD requirements.txt . 
RUN python3 -m pip install -r requirements.txt
RUN python3 -m spacy download en_core_web_sm

ADD scraper.py .

ENTRYPOINT ["python3", "/app/scraper.py"]

RUN echo 'done'