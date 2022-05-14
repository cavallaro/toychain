FROM python:3.9-slim

WORKDIR /tmp/toychain

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/toychain .

ENV FLASK_APP "api/app.py"

ENTRYPOINT ["flask", "run", "--host", "0.0.0.0"]
