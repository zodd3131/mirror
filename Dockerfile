FROM python:3.10-slim

RUN mkdir /code
WORKDIR /code
COPY ./requirements.txt /code
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN apt-get update && apt-get -y install tcpdump
RUN useradd mirror

COPY src/mirror /code/mirror

RUN chown -R mirror:mirror ./
# USER mirror
EXPOSE 8000
ENTRYPOINT [ "python", "-m", "mirror.main" ]
