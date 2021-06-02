FROM python:3

ADD tmdb.py /

RUN pip install requests boto3

CMD [ "python", "./tmdb.py" ]