FROM python:3.10-alpine

RUN apk --no-cache add bash postgresql-client yaml-dev && \
    addgroup user && \
    adduser -s /bin/bash -D -G user user

WORKDIR /pingou

ADD requirements.txt /pingou
#
RUN apk --no-cache add --virtual build-dependencies gcc g++ make musl-dev libffi-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    apk del build-dependencies && \
    rm requirements.txt

RUN chown -R user:user /pingou

ADD run.py ./
ADD pingou/ pingou/
ADD static/ static/


USER user

ENTRYPOINT ["python", "run.py"]
