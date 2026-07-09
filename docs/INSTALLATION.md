# Instalación

## Requisitos Previos

- Python 3.11+ (3.10 funciona pero el Dockerfile usa 3.11)
- PostgreSQL 14+ (o una instancia gestionada en Railway)
- WordPress con REST API habilitada y Application Passwords
- Clave de API de Anthropic (Claude)

## Instalación en Linux/macOS

```bash
# 1. Clonar el repositorio
git clone https://github.com/carloscheco-cloud/NeuroDiario.git
cd NeuroDiario

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Descargar modelo de spaCy
python -m spacy download es_core_news_lg

# 5. Configurar variables de entorno
cp .env.example .env
nano .env  # Editar con tus credenciales

# 6. Inicializar la base de datos
python -c "from neurodiario.db.database import init_db; init_db()"

# 7. Verificar fuentes RSS
python verificar_fuentes.py

# 8. Ejecutar el scheduler
python -m scheduler.auto_scheduler
```

## Instalación en Windows

```powershell
git clone https://github.com/carloscheco-cloud/NeuroDiario.git
cd NeuroDiario
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download es_core_news_lg
copy .env.example .env
# Editar .env con notepad
python -c "from neurodiario.db.database import init_db; init_db()"
python -m scheduler.auto_scheduler
```

## Verificación Post-Instalación

```bash
# Verificar fuentes RSS
python verificar_fuentes.py

# Ejecutar prueba de ingesta
python -m neurodiario.scheduler.pipeline

# Verificar estado de la BD
python -m neurodiario.tools.Db_stats
```

## Troubleshooting de Instalación

- **spaCy model not found**: ejecutar `python -m spacy download es_core_news_lg`
- **psycopg2 build fails**: instalar `libpq-dev` (Ubuntu) o usar `psycopg2-binary`
- **WordPress 401**: verificar que la URL use HTTPS y que Application Passwords estén habilitadas
