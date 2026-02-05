ISF Furnace Simulation (Zinc Plant)
===================================

This project contains a simplified steady‑state simulation of an Imperial Smelting Furnace (ISF) used in zinc/lead smelting plants.

The model focuses on:

- Feed and coke input specification (mass flow and composition)
- Elemental mass balance across the furnace
- Distribution of Zn, Pb and other elements to metal, slag and off‑gas
- Simple energy/KPI calculations (e.g. coke rate, energy per tonne of zinc)

> **Note**  
> This is an educational/engineering‑concept model, not a detailed CFD or thermodynamic equilibrium simulation. It uses lumped parameters and user‑defined recoveries.

## Project structure

- `requirements.txt` – Python dependencies
- `isf_simulation/` – Python package with the core model
  - `__init__.py`
  - `model.py` – data classes and ISF furnace model
- `run_isf_example.py` – example script to run a typical ISF scenario

## Installation

1. Create and activate a virtual environment (recommended).
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage (command‑line example)

Run the example scenario:

```bash
python run_isf_example.py
```

This will:

- Define a typical sinter feed, coke and air flow
- Run the ISF furnace steady‑state simulation
- Print mass balance tables for feed and products (metal, slag, off‑gas)
- Print simple KPIs (e.g. zinc recovery, coke rate per tonne zinc)

You can modify the inputs in `run_isf_example.py` to represent your own plant conditions (feed composition, feed rate, coke rate, recoveries, etc.).

## ISF dashboard (web UI)

An interactive dashboard is provided in `dashboard_app.py` using Streamlit.

1. Install dependencies (as above).
2. Run the dashboard:

```bash
streamlit run dashboard_app.py
```

This will start a local web app with:

- A sidebar to adjust feed composition and operating conditions
- Graphs of zinc recovery and coke energy intensity versus coke rate
- A simulation table across a range of coke rates
- Simple text recommendations based on recovery, energy intensity, and production vs target

