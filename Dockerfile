FROM python:3

ADD tmdb.py /

ADD chunks /chunks

RUN pip install requests boto3

CMD [ "python", "./tmdb.py" ]