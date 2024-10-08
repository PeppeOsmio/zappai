FROM python:3.12

WORKDIR /app

COPY pyproject.toml poetry.lock* poetry.toml /app/

RUN pip install --no-cache-dir poetry

RUN poetry install --no-interaction --no-ansi

COPY . /app

# install the main folder of the project in the venv also
RUN poetry install --no-interaction --no-ansi

EXPOSE 8000

RUN chmod +x ./entrypoint.sh

ENTRYPOINT [ "./entrypoint.sh" ]