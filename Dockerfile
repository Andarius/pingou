FROM python:3.8-alpine

RUN apk --no-cache add bash postgresql-client  yaml-dev && \
    addgroup user && \
    adduser -s /bin/bash -D -G user user

WORKDIR /pingou

ADD requirements.txt /pingou
#
RUN  apk --no-cache add --virtual build-dependencies gcc g++ make musl-dev libffi-dev && \
     pip install -r requirements.txt && \
     apk del build-dependencies && \
     rm requirements.txt
RUN  chown -R user:user /pingou

ADD run.py ./
ADD env.py ./
ADD pg.py ./
ADD logs.py ./
ADD pingou/ pingou/
ADD static/ static/


RUN mkdir /logs && chown -R user:user /logs
VOLUME /logs

USER user

ENTRYPOINT ["python", "run.py"]