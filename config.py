from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent           
DATA_DIR = BASE_DIR / "data"                         
TMP_DIR = DATA_DIR / "tmp"                            
TEMP_MEI_DIR = DATA_DIR / "temp_generated_mei"         
SV_TO_MEI_DIR = DATA_DIR / "sv_to_mei"                 

TEMPLATES_DIR = BASE_DIR / "templates"                  
STATIC_DIR = BASE_DIR / "static"                       
MEI_TEMPLATES_DIR = BASE_DIR / "resources" / "mei_templates"

for d in [DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

for d in [TMP_DIR, TEMP_MEI_DIR, SV_TO_MEI_DIR]:
    d.mkdir(parents=True, exist_ok=True)