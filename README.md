# Musical Data Processing Toolkit

A lightweight web-based toolkit for **cleaning, aligning, and enriching musical analysis data**.  
Built with FastAPI + Jinja2, it provides three utilities designed for researchers, musicologists, and MIR developers who work with **CSV timing data**, **audio feature extraction**, and **MEI scores**.

---

## Features

### 1. Correct Beats & Tempo
Upload a CSV containing raw timing information and generate:
- A corrected **measure.beat** sequence  
- Optional handling of **pickup/anacrusis**  
- **Tempo (BPM)** calculations between beat positions  
- A clean, standardized CSV ready for further processing  

---

### 2. Align Plugin Data to Beats
Upload:
- A **base CSV** (usually containing timestamps and measure/beat information)
- A **plugin CSV** (e.g., Sonic Visualiser PowerCurve or other audio descriptors)

The tool:
- Aligns plugin values to each beat's time window  
- Aggregates values (`mean`, `max`, `min`, or plugin-specific logic)
- Outputs a merged CSV combining structural and audio-derived information  

---

### 3. Insert CSV Values into MEI Scores
Upload:
- An **MEI/XML score**
- A **CSV** containing musical attributes mapped to `measure.beat`

The tool can insert:
- **Tempo changes**
- **Dynamics**
- **Annotations** (with optional labels)

---

## Technology

- **FastAPI** backend  
- **Jinja2** templating  
- **Python services** for CSV processing, beat correction, and MEI manipulation  
- Clean, isolated router structure for easy extension  
- Simple server-side file handling with temporary work directories

---

## Installation

```bash
git clone https://github.com/yourrepo/yourproject
cd yourproject
pip install -r requirements.txt
