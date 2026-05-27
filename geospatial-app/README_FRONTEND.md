# 🌍 Geospatial Image Analysis with Quantum Computing

Una interfaz moderna y futurista para analizar imágenes georeferenciadas utilizando IA, embeddings vectoriales y clustering cuántico.

## 🚀 Características

✨ **Upload de Imágenes** - Soporte para hasta 20 imágenes (JPEG, PNG, TIFF, HEIC)
🔍 **Extracción EXIF** - Lectura automática de metadatos GPS
🧠 **NLP & Vision** - Generación de etiquetas y detección de objetos (YOLO)
📊 **Embeddings Vectoriales** - Conversión de etiquetas a vectores semánticos
⚛️ **Clustering Cuántico** - Optimización QAOA en datos espaciales
🗺️ **Visualización Interactiva** - Mapa global y tabla de resultados
🌐 **Globo Terrestre 3D** - Visualización cinética con Three.js

## 📋 Requisitos

- Python 3.8+
- pip o conda
- 500MB de espacio disponible (para modelos)

## 🔧 Instalación

### 1. Clonar el repositorio

```bash
cd geospatial-app
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crear archivo `.env`:

```env
OPENAI_API_KEY=tu_api_key_aqui
IBM_QUANTUM_CHANNEL=ibm_quantum
IBM_QUANTUM_TOKEN=tu_token_opcional
```

### 5. Descargar modelos

```bash
# YOLO
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Sentence Transformers
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

## 🎯 Uso Rápido

### Iniciar la aplicación

```bash
python app.py
```

La aplicación estará disponible en: **http://localhost:5000**

### Flujo de trabajo

1. **Upload** - Arrastra o haz clic para seleccionar imágenes (máx 20)
2. **Procesamiento** - Haz clic en "START PROCESSING"
3. **Monitoreo** - Observa el pipeline en tiempo real
4. **Visualización** - Explora el globo 3D y el mapa interactivo
5. **Análisis** - Revisa etiquetas y objetos detectados

## 🏗️ Estructura del Proyecto

```
geospatial-app/
├── app.py                          # API Flask principal
├── requirements.txt                # Dependencias Python
├── templates/
│   └── index.html                 # Interfaz HTML principal
├── static/
│   ├── css/
│   │   └── style.css              # Estilos (tema espacial)
│   └── js/
│       ├── app.js                 # Lógica principal
│       └── globe.js               # Extensiones del globo
├── src/
│   ├── pipeline.py                # Pipeline de procesamiento
│   ├── exif_extractor.py          # Extracción EXIF/GPS
│   ├── nlp.py                     # Procesamiento NLP
│   ├── embeddings.py              # Generación de embeddings
│   ├── vector_db.py               # Base de datos vectorial (ChromaDB)
│   ├── geospatial.py              # Procesamiento geoespacial
│   ├── vision.py                  # Visión por computadora
│   └── quantum_spatial_optimizer.py # Clustering cuántico
├── uploads/                        # Imágenes subidas (temporal)
├── output/                         # Resultados y mapas generados
└── chroma_db/                      # Base de datos vectorial
```

## 🔌 API Endpoints

### Health Check
```
GET /api/health
```

### Upload Images
```
POST /api/upload
Content-Type: multipart/form-data
Body: { images: [File, File, ...] }
Response: { success, uploaded_count, images, errors }
```

### Process Pipeline
```
POST /api/process
Content-Type: application/json
Body: { image_paths: ["path/to/img1", "path/to/img2", ...] }
Response: { images, clusters, summary, pipeline_steps }
```

### Generate Map
```
POST /api/generate-map
Content-Type: application/json
Body: { images: [{ latitude, longitude, tags, ... }, ...] }
Response: { success, map_path, center, bounds }
```

### Statistics
```
GET /api/stats
Response: { total_images_uploaded, total_size_mb, ... }
```

## 🎨 Características de Diseño

- **Tema Oscuro** - Interfaz moderna con gradientes espaciales
- **Animaciones Fluidas** - Transiciones suaves y efectos visuales
- **Diseño Responsivo** - Compatible con móviles y escritorio
- **Efectos de Física** - Planetas flotantes y estrellas parpadeantes
- **Visualización de Pipeline** - Pasos animados del procesamiento

## ⚛️ Quantum Features

El clustering utiliza **QAOA (Quantum Approximate Optimization Algorithm)**:
- Optimización cuántica de agrupamientos geoespaciales
- Simulador Aer de Qiskit
- Soporte opcional para IBM Quantum

## 📊 Resultados

Los resultados se guardan en:
- `output/interactive_map.html` - Mapa interactivo
- ChromaDB - Base de datos vectorial local

## 🐛 Solución de Problemas

### Error de conexión API
```
✓ Asegúrate de que Flask está ejecutándose
✓ Verifica http://localhost:5000
✓ Comprueba los logs en la terminal
```

### Modelos no descargados
```bash
# YOLO
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Sentence Transformers
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### Problemas con GPU
Por defecto usa CPU. Para GPU:
```python
# En app.py, agregar:
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
```

## 📈 Mejoras Futuras

- [ ] Autenticación de usuarios
- [ ] Base de datos persistente (PostgreSQL)
- [ ] Exportación de resultados (PDF, JSON)
- [ ] Procesamiento por lotes
- [ ] Estadísticas en tiempo real
- [ ] Integración con IBM Quantum Real Hardware
- [ ] Visualización 3D avanzada con Babylon.js
- [ ] Cache inteligente

## 📝 Licencia

MIT License - Ver LICENSE para detalles

## 👤 Autor

Desarrollado con ❤️ para análisis geoespacial inteligente

## 📧 Soporte

Para reportar bugs o sugerencias, crear un issue en el repositorio.

---

**Nota:** Asegúrate de tener conexión a Internet para descargar modelos la primera vez.
