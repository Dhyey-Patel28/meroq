# Exportable Insight Reports

Meroq can generate a local Markdown report from the current dashboard run.

## Purpose

The report is designed to make each analysis reproducible and easier to share. It summarizes the major outputs from a run without exposing local API keys or cache files.

## Included sections

- Executive summary
- Primary model signal
- Simple train/test metrics
- Sentiment overlay
- Monte Carlo risk simulation
- Watchlist highlights
- Model comparison snapshot
- Interpretation notes and limitations

## Outputs

The Report tab provides:

- Markdown report download
- Watchlist CSV download, when a watchlist scan was run

## Privacy and local data

Reports are generated locally from already-rendered results. They do not include:

- `.env` values
- API keys
- SQLite databases
- Hugging Face cache paths
- raw credential information

## Limitations

Reports are not investment advice. They are intended for educational, research, and portfolio-monitoring notes. They should be interpreted alongside the app's model-risk documentation.
