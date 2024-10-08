# ZappAI

Applicazione per l'assistenza nella piantagione e nel raccolto.

## Applicazione di intelligenza artificiale generativa per ottimizzare le pratiche agricole sostenibili

Questa tesi potrebbe esplorare l'utilizzo di modelli di intelligenza artificiale
generativa (come reti neurali o algoritmi genetici) per ottimizzare le pratiche agricole
sostenibili. Ad esempio, l'AI potrebbe essere utilizzata per predire il momento ottimale per
seminare o raccogliere colture locali, considerando dati ambientali e stagionali.

## Manuale utente

L’installazione dell’app richiede una macchina su cui è installato Docker e Docker Compose . Di seguito i passi per l’installazione (da eseguire una sola volta):

1. Creare un account su Copernicus Data Store e copiare il Personal Access Token nella variabile d’ambiente `ZAPPAI_CDS_API_KEY` nel file `env_files/backend.env`. Compilare il resto delle variabili d’ambiente secondo gli esempi trovati in `docs/env_files_examples`, creando quindi anche un file `env_files/postgres.env`.

1. Avviare il progetto Docker Compose:

```bash
docker compose up -d
```

2. Una volta avviata l’app, sarà necessario effettuare delle procedure preliminari nel container del backend. Sarà necessario quindi aprire una shell nel container:

```bash
docker compose exec -it backend bash
```

3. Attivare il virtual environment Python:

```bash
source .venv/bin/activate
```

4. Avviare lo script per scaricare i dati climatici futuri del dataset CMIP5 (tempo di esecuzione fino a 40 minuti):

```bash
python scripts/download_future_climate_data.py
```

5. Importare i dati sul rendimento delle coltivazioni per l’addestramento del modello per ogni pianta:

```bash
python scripts/import_crops_yield_data.py
```

6. Importare i dati climatici storici del dataset ERA5 per l’addestramento del modello per il rendimento delle coltivazioni:

```bash
python scripts/import_past_climate_data.py  
```

7. Addestrare e salvare i modelli per la previsione del rendimento delle coltivazioni:

```bash
python scripts/create_crop_yield_models.py
```

Terminati questi passi l’applicazione (frontend e API) è fruibile in HTTP sulla porta 80 del sistema.
È necessario creare delle utenze che possano usare l’app. Per gestire le utenze è necessario usare la shell nel container backend attivando il virtual environment Python (passi 1 e 2 precedenti). Di seguito i comandi:

1. Creazione di un utente:

```bash
python scripts/create_user.py –-username "<username>" -–password "<password>" -–email "<email>" -–name "<name>"
```

2. Rimozione di un utente:

```bash
python scripts/delete_user.py –-username "<username>"
```

3. Logout di un utente da tutti i dispositivi:

```bash
python scripts/logout_user.py –-username "<username>"
```

È possibile consultare la documentazione Swagger dell’API all’url /api/docs.
