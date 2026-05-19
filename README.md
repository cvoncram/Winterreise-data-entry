# 🎵 Tools for _Winterreise_ Data Entry 🎼

This application runs locally in your browser. It decompresses Sonic Visualiser session files, extracts the data layers, aggregates them according to user input, 
and finally maps this data onto and inserts it in empty MEI-XML files. It is also possible to generate new MEI-XML files from metadata.

This page and these tools were created by Clemens von Cramon as part of the project [Creating Schubert’s „Die Winterreise“ in Performance with Dietrich Fischer-Dieskau](https://github.com/Joshua-Neumann/Fischer_Dieskau_Winterreise).

The process and calculations of mapping dynamic values onto beat markings and creating interpreted dynamics values is inspired by and closely resembles the [Dyn-a-matic tool](https://mazurka.org.uk/software/online/dynamatic/) created by the [Mazurka Project](https://mazurka.org.uk/).

---

## Installation (Linux/macOS)

### Prerequisites

Python 3.12.3 and pip 24.0 or higher are required.

### Installing and starting the application (in command line)

After finishing the installation, you will be able to start the application by opening the executable script start_app.sh.

#### Linux and macOS

```bash
# Create a new folder for the app and move into it
mkdir Winterreise_app
cd Winterreise_app

# Clone the repository
git clone git@github.com:cvoncram/Winterreise-data-entry.git

# Create a Python virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install Python requirements
pip install -r requirements.txt

# Deactivate the virtual environment
deactivate
```
#### Windows

```powershell

# Create a new folder for the app and move into it
mkdir Winterreise_app
Set-Location Winterreise_app

# Clone the backend repository
git clone git@github.com:cvoncram/Winterreise-data-entry.git

# Create a Python virtual environment
python -m venv venv

# Activate the virtual environment
venv\Scripts\Activate.ps1

# Install Python requirements
pip install -r requirements.txt

# Deactivate the virtual environment
deactivate

```

#### Docker (Linux/macOS)

```bash

# Create a new folder for the app and move into it
mkdir Winterreise_app
cd Winterreise_app

# Clone the backend repository
git clone git@github.com:cvoncram/Winterreise-data-entry.git

cd Winterreise-data-entry

# Build the Docker image
docker build -t data-entry .

# Run the Docker container
docker run -d   -p 8000:8000   --name data-entry-app   data-entry
# You can now access the application in your browser under http://localhost:8080

# Stop the Docker container 
docker stop data-entry

```

---

## Used frameworks, libraries, and packages

- [FastAPI](https://fastapi.tiangolo.com/) for HTTP routing and services
- [Jinja2](https://jinja.palletsprojects.com/en/stable/) for templating
- [NumPy](https://numpy.org) for additional mathematical operations
- [lxml](https://lxml.de/) for processing XML in Python

---
