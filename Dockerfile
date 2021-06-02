FROM python:3

ADD tmdb.py /
ADD start.sh /

RUN pip install requests boto3

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install

CMD [ "./start.sh" ]