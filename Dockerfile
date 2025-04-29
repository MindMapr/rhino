# Select Python version
FROM python:3.13-slim

# Set working directory
WORKDIR /code

# copy requirements to working directory
COPY ./requirements.txt .

# Install newest version of pip
RUN python -m pip install --upgrade pip

# Install app packages from requirements
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]