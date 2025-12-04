from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent              # backend/
DATA_DIR = BASE_DIR / "data"                            # backend/data
TMP_DIR = DATA_DIR / "tmp"                              # backend/data/tmp
TEMP_MEI_DIR = DATA_DIR / "temp_generated_mei"          # backend/data/temp_generated_mei
SV_TO_MEI_DIR = DATA_DIR / "sv_to_mei"                  # backend/data/sv_to_mei

TEMPLATES_DIR = BASE_DIR / "templates"                  # backend/templates
STATIC_DIR = BASE_DIR / "static"                        # backend/static
MEI_TEMPLATES_DIR = BASE_DIR / "resources" / "mei_templates"

# Create folders once
for d in [DATA_DIR]:
    d.mkdir(parents=True, exist_ok=True)

for d in [TMP_DIR, TEMP_MEI_DIR, SV_TO_MEI_DIR]:
    d.mkdir(parents=True, exist_ok=True)    
