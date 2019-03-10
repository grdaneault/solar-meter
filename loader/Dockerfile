FROM python:3.7

COPY requirements.txt /code/
RUN pip install -r /code/requirements.txt

COPY load_data.py /code/

CMD ["python", "/code/load_data.py"]