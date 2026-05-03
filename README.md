# Geospatial Image Tagging using Natural Language

## Description

This project is a standalone spatial application that enables semantic tagging and retrieval of georeferenced images using natural language.

It combines:
- Computer Vision
- Natural Language Processing
- Vector Databases
- Geospatial filtering

Users can search images using natural language queries such as:
"residential area with trees near Tunis"

---

## Features

- Store georeferenced images (latitude, longitude)
- Generate embeddings from images and text
- Semantic search using natural language
- Spatial filtering (radius, location-based queries)
- Automatic image tagging (optional)

---

## Tech Stack

### AI / NLP
- OpenAI CLIP for image-text embeddings
- spaCy for text preprocessing
- BLIP for image captioning (optional)

### Databases
- ChromaDB for vector similarity search
- PostgreSQL with PostGIS for spatial queries

### Backend
- FastAPI for REST API

### Image Processing
- OpenCV
- Pillow

### DevOps
- Docker

---

## Architecture

```
                ┌──────────────┐
                │   Images     │
                └──────┬───────┘
                       ↓
                Preprocessing
                       ↓
                 CLIP / BLIP
                       ↓
                Embeddings
                       ↓
        ┌──────────────┴──────────────┐
        ↓                             ↓
 Vector Database (ChromaDB)   PostgreSQL + PostGIS
 (semantic search)           (spatial filtering)
        ↓                             ↓
        └──────────────┬──────────────┘
                       ↓
                    FastAPI
                       ↓
                     Clients
```

---

## Project Structure

```
project/
│── app/
│   │── api/              # FastAPI routes
│   │── services/        # Core business logic
│   │── models/          # Data schemas
│   │── db/              # Database connections
│   │── embeddings/      # CLIP and NLP logic
│
│── data/
│   │── images/          # Stored images
│
│── scripts/
│   │── ingest.py        # Data ingestion pipeline
│
│── docker/
│── requirements.txt
│── README.md
```

---

## Installation

### Clone repository
```bash
git clone https://github.com/your-username/geospatial-image-tagging.git
cd geospatial-image-tagging
```

### Create virtual environment
```bash
python -m venv venv
source venv/bin/activate
```

### Install dependencies
```bash
pip install -r requirements.txt
```

---

## Run the project

```bash
uvicorn app.main:app --reload
```

API documentation:
```
http://127.0.0.1:8000/docs
```

---

## API Endpoints

### Upload Image
```
POST /upload
```

### Search Images
```
POST /search
```

Example request:
```json
{
  "query": "agricultural land with trees",
  "lat": 36.8,
  "lon": 10.1,
  "radius": 5
}
```

---

## System Workflow

1. Images are encoded using CLIP into embeddings
2. Text queries are converted into the same vector space
3. Similarity search is performed using ChromaDB
4. Results are filtered using spatial constraints (PostGIS)

---

## Example Query

Input:
"urban area with roads"

Output:
- Images semantically similar to the query
- Filtered by geographic proximity

---

## Challenges

- Combining vector similarity with spatial filtering
- Managing embedding quality
- Handling large-scale image datasets

---

## Future Improvements

- Frontend interface with map visualization
- Fine-tuning CLIP on domain-specific datasets
- Real-time image processing pipeline
- Multi-modal search (image + text input)

---



---

## Author

Jemili Melek & Khalfalli Nourane
