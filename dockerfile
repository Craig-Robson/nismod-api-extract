FROM python:3.8
RUN apt-get -y update
RUN apt-get -y install libgdal-dev

COPY requirements.txt /
RUN pip install -r requirements.txt

COPY main.py /
RUN mkdir /data
RUN mkdir /data/outputs

ENTRYPOINT python main.py