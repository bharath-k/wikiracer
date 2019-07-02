FROM python:3
COPY . /wikiracer
WORKDIR /wikiracer
RUN pip install -r requirements.txt
EXPOSE 8080
ENV PYTHONPATH="${PYTHONPATH}:."
CMD ["python", "wikiracer/app.py"]
