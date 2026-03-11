# Armenian Genocide Coverage in the Australian Press (Trove Dataset)

This repository contains a dataset of newspaper metadata related to
coverage of the Armenian Genocide in the Australian press.

The dataset was extracted from Trove, the digital discovery platform of
the National Library of Australia, using the Trove API.

The project was developed as part of the **Open Data Armenia
initiative**, which aims to collect, document, and preserve references
to Armenian cultural heritage and historical events across international
archives, libraries, and digital collections.

## Data Source

Trove -- National Library of Australia\
https://trove.nla.gov.au

Trove aggregates digitized materials from the National Library of
Australia and partner institutions, including newspapers, photographs,
maps, books, and research publications.

This dataset focuses on **newspaper records** related to the Armenian
Genocide and humanitarian responses reported in the Australian press.

## Dataset Description

The dataset contains **metadata only**, not the original articles.

Each record includes a link to the original item on Trove.

### Column Description

- **title** — Newspaper article title  
- **date_or_period** — Publication date  
- **author_or_creator** — Article author (if available)  
- **description_or_abstract** — Article snippet provided by Trove  
- **url_to_original_object** — Direct link to the Trove article  
- **trove_category** — Trove content category  
- **trove_record_type** — Type of Trove record  
- **trove_id** — Unique Trove identifier  
- **trove_url** — Trove record URL

## Methodology

The dataset was collected using the Trove API with keyword-based search
queries related to:

-   Armenian deportations
-   massacres and atrocities
-   refugee relief and humanitarian aid
-   Armenian refugees and orphans

The scraper implements:

-   Trove API pagination
-   deduplication of records
-   metadata extraction
-   export to structured formats (JSONL and CSV)

The dataset focuses on the historical period **1915--1923**,
corresponding to the years of the Armenian Genocide and its immediate
aftermath.

## Files

data/trove_genocide_au_press_clean.csv

## Use Cases

The dataset may support research in:

-   Armenian diaspora history
-   international press coverage of the Armenian Genocide
-   humanitarian relief movements
-   digital humanities and historical data analysis

## Project

Prepared for **Open Data Armenia**.

Open Data Armenia works to identify and document Armenian historical and
cultural heritage across global archives and digital collections.
