# Smart Document Processing and Management System

A full-stack, enterprise-grade digital document processing and management system built with **FastAPI**, **SQLite**, **Local File Storage**, and a responsive **HTML5/CSS3/JavaScript** frontend. Engineered with a decoupled domain architecture (thin routes, domain services, repository abstraction, pluggable storage) designed for seamless migration to **Amazon Web Services (AWS S3, Lambda, API Gateway, DynamoDB)** in Phase 2.

---

## 1. Project Overview

The **Smart Document Processing and Management System** solves digital clutter and compliance challenges by providing:
- **Centralized Digital Repository**: Safe upload, storage, preview, and download of multi-format documents (PDF, DOC/DOCX, PPT/PPTX, XLS/XLSX, TXT, PNG, JPG/JPEG).
- **Automated Rule-Based Categorization**: Transparent heuristic classification assigning documents to Academic, Research, Projects, Personal, Business, or Other, with manual override support.
- **Cryptographic Duplicate Detection**: Content hashing via SHA-256 preventing redundant storage and duplicate upload collisions.
- **Real-Time Analytics & Audit Trail**: Interactive Chart.js data visualizations for category and file-type distribution, storage quota meters, and chronological activity logging.
- **AWS Migration Ready**: Pluggable storage and repository interfaces decoupling business logic from underlying persistence engines.

---

## 2. Technology Stack

| Layer | Technologies |
|---|---|
| **Backend Runtime** | Python 3.12, FastAPI, Starlette, Uvicorn (ASGI) |
| **Data Validation** | Pydantic v2 & Pydantic-Settings |
| **Persistence & ORM** | SQLite, SQLAlchemy 2.0 (Declarative Base, Mapped Columns) |
| **File Storage** | `LocalStorageProvider` (Local disk repository with path traversal protection) |
| **Frontend UI** | Semantic HTML5, Modular CSS3 (Dark navy-purple sidebar, CSS variables), Vanilla ES6 JavaScript |
| **Data Visualization** | Chart.js 4.4.1 (Doughnut and Bar visualizations with responsive canvas lifecycle) |
| **Test Suite** | Pytest 9.2, FastAPI TestClient, AnyIO |
| **Target Cloud Stack** | Amazon S3, AWS Lambda, Amazon API Gateway, DynamoDB, Amazon CloudWatch (Phase 2) |

---

## 3. Directory Structure

```
smart-document-manager/
├── frontend/                     # Modern vanilla frontend
│   ├── index.html                # App shell with unified SaaS navigation
│   ├── css/                      # Modular stylesheets & design tokens
│   │   ├── variables.css         # Dark navy-purple, purple gradient, colors
│   │   ├── layout.css            # Sidebar, topbar, responsive containers
│   │   ├── components.css        # Cards, tables, forms, dropzone, modals, toasts
│   │   └── main.css              # Entry stylesheet bundle
│   └── js/                       # Modular JavaScript controllers
│       ├── api.js                # Reusable fetch client with error/latency tracking
│       ├── state.js              # Client state manager & backend sync engine
│       ├── navigation.js         # Single-page router for 6 sections
│       ├── dashboard.js          # Chart.js integration, stats, storage meter
│       ├── documents.js          # Search, filters, sort, preview, download, delete
│       ├── upload.js             # Drag-and-drop, queue, progress, validation
│       ├── categories.js         # Default 6 categories, CRUD modal dialogs
│       ├── activity.js           # Audit trail timeline, search, and filters
│       ├── settings.js           # Profile, preferences toggles, security, storage
│       └── app.js                # App coordinator, modal and toast engine
├── backend/                      # Python 3.12 + FastAPI backend
│   ├── main.py                   # FastAPI entry point, CORS, static mounts
│   ├── api/                      # REST API routes
│   │   └── v1/
│   │       ├── router.py         # Aggregated v1 router
│   │       └── endpoints/        # Modular API endpoints
│   │           ├── health.py     # System health & dependency check
│   │           ├── documents.py  # Document upload, search, preview, download, delete
│   │           ├── categories.py # Category CRUD with safe reassignment
│   │           ├── dashboard.py  # Aggregated metrics & distributions
│   │           ├── activities.py # Chronological audit trail & search
│   │           └── settings.py   # System preferences & profile
│   ├── config/                   # Pydantic BaseSettings configuration
│   │   └── settings.py
│   ├── database/                 # SQLite database layer
│   │   ├── base.py               # Declarative ORM base
│   │   └── session.py            # SQLite engine, sessions, ping probe
│   ├── models/                   # SQLAlchemy domain models
│   │   ├── document.py           # Document metadata & relations
│   │   ├── category.py           # Taxonomy categories
│   │   ├── activity.py           # Audit event log
│   │   └── settings.py           # System configuration
│   ├── schemas/                  # Pydantic request & response schemas
│   │   ├── document.py
│   │   ├── category.py
│   │   ├── activity.py
│   │   ├── dashboard.py
│   │   └── settings.py
│   ├── storage/                  # Pluggable storage abstraction
│   │   ├── base.py               # Abstract StorageProvider interface
│   │   └── local.py              # LocalStorageProvider implementation
│   ├── repositories/             # Pluggable repository abstraction
│   │   ├── base.py               # Generic BaseRepository interface
│   │   ├── document_repository.py
│   │   ├── category_repository.py
│   │   ├── activity_repository.py
│   │   └── settings_repository.py
│   ├── services/                 # Decoupled business logic
│   │   ├── document_service.py
│   │   ├── category_service.py
│   │   ├── activity_service.py
│   │   ├── dashboard_service.py
│   │   └── settings_service.py
│   └── utils/
│       ├── logger.py             # Structured logging
│       └── exceptions.py         # Custom application exceptions
├── local_storage/                # Local document repository (Phase 1)
│   ├── documents/
│   └── temp/
├── tests/                        # Comprehensive automated test suite
│   ├── conftest.py               # Test fixtures & isolated SQLite/storage
│   ├── test_health.py            # API health endpoint tests
│   ├── test_database.py          # SQLite engine & session tests
│   ├── test_storage.py           # Storage provider lifecycle & traversal tests
│   ├── test_frontend.py          # Static asset & UI template serving
│   ├── test_api_documents.py     # Upload, download, duplicate detection, preview
│   ├── test_api_categories.py    # Category CRUD & protection
│   ├── test_api_organization.py  # Search, filter, sorting, metadata extraction
│   ├── test_api_dashboard_and_activity.py # Live analytics & activity trail
│   ├── test_api_settings.py      # Profile & preference settings
│   └── test_persistence_integration.py # Restart & persistence lifecycle tests
├── .env                          # Local environment variables
├── .env.example                  # Template configuration
├── .gitignore                    # Git exclusions
├── requirements.txt              # Production & test dependencies
└── README.md                     # Complete project documentation
```

---

## 4. Environment Variables

Configuration is loaded via Pydantic BaseSettings from `.env` or system environment variables:

| Variable | Type | Default | Description |
|---|---|---|---|
| `APP_NAME` | `str` | `"Smart Document Processing System"` | Human-readable application name |
| `APP_ENV` | `str` | `"development"` | Environment mode (`development`, `testing`, `production`) |
| `DEBUG` | `bool` | `True` | Enable debug logs and verbose errors |
| `HOST` | `str` | `"127.0.0.1"` | Host address for ASGI server |
| `PORT` | `int` | `8000` | Port for ASGI server |
| `DATABASE_URL` | `str` | `"sqlite:///./smart_document_manager.db"` | SQLite database connection string |
| `STORAGE_TYPE` | `str` | `"local"` | Storage driver (`local` for Phase 1, `s3` for Phase 2) |
| `LOCAL_STORAGE_DIR` | `str` | `"./local_storage/documents"` | Root directory for stored files |
| `MAX_UPLOAD_SIZE_MB` | `int` | `20` | Maximum upload size per file (in megabytes) |
| `ALLOWED_ORIGINS` | `str` | `"*"` | CORS allowed origins (comma-separated or `*`) |

---

## 5. Database Setup & Architecture

### Schema Overview
The SQLite database contains four core tables with primary keys, foreign keys, indexes, and constraints:
1. **`documents`**:
   - `id` (VARCHAR(36), PK): UUID identifier.
   - `filename`, `original_filename` (VARCHAR(255)): Clean and raw file names.
   - `file_path` (VARCHAR(500)): Relative path in storage.
   - `file_size` (INTEGER): File size in bytes.
   - `file_type`, `file_extension` (VARCHAR): Classified format and lowercase extension.
   - `mime_type` (VARCHAR(100)): Verified MIME type.
   - `sha256_hash` (VARCHAR(64), Index): Cryptographic digest for duplicate detection.
   - `category_id` (VARCHAR(36), FK $\rightarrow$ `categories.id` ON DELETE SET NULL).
   - `category_name` (VARCHAR(100), Index): Fast category queries.
   - `is_manually_categorized` (BOOLEAN): Manual override flag.
   - `created_at`, `updated_at` (DATETIME): Automatic timestamps.
   - Compound index: `idx_doc_search` on `(filename, category_name, file_type, file_extension)`.

2. **`categories`**:
   - `id` (VARCHAR(36), PK): UUID identifier.
   - `name` (VARCHAR(100), Unique, Index): Category name.
   - `description` (TEXT), `color` (VARCHAR(20)), `icon` (VARCHAR(50)).
   - `is_default` (BOOLEAN): Protection flag for system categories (e.g., `Other`).
   - Default categories seeded automatically: *Academic, Research, Personal, Projects, Business, Other*.

3. **`activities`**:
   - `id` (VARCHAR(36), PK): UUID identifier.
   - `activity_type` (VARCHAR(50), Index): `upload`, `download`, `delete`, `category_change`, `category_create`, `category_delete`.
   - `title` (VARCHAR(255)), `description` (TEXT): Audit descriptions.
   - `document_id` (VARCHAR(36), Nullable), `document_name` (VARCHAR(255)).
   - `category_name` (VARCHAR(100)), `status` (VARCHAR(50)).
   - Compound index: `idx_activity_type_time` on `(activity_type, created_at)`.

4. **`system_settings`**:
   - `id` (INTEGER, PK, default=1): Single-row system configuration.
   - `full_name`, `email`, `role`, `auto_categorize`, `duplicate_detection`, `default_category`, `max_upload_size_mb`, `storage_quota_mb`.

### Automatic Database Initialization
Tables are created and default categories seeded automatically on application startup. To manually initialize or inspect:
```python
from backend.database.session import init_db
init_db()
```

---

## 6. Installation & Quick Start

### 1. Set Up Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# Linux/macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
```

### 4. Run the Application
```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

- **Frontend Web Application**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc API Documentation**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **System Health Probe**: [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## 7. REST API Documentation

### Authentication & Account Management
- `POST /api/auth/register` — Create new user account with unique email and username, password hashing via bcrypt, returning signed JWT token and user profile.
- `POST /api/auth/login` — Sign in via username or email and password; returns JWT access token and user info.
- `GET /api/auth/me` — Retrieve currently authenticated user's profile details (`Authorization: Bearer <token>`).
- `PUT /api/auth/profile` — Update user profile full name or email address.
- `POST /api/auth/change-password` — Change password after verifying existing password.
- `POST /api/auth/logout` — Client session sign out.

### Health
- `GET /api/health` — Probes SQLite database connectivity and local storage directory permissions.

### Documents
- `GET /api/documents` — Paginated list of documents with compound filters (`category`, `file_type`, `file_extension`, `date_from`, `date_to`, `min_size`, `max_size`) and sorting (`sort_by`: `date`, `name`, `size`, `category`; `sort_order`: `asc`, `desc`).
- `GET /api/documents/search?q={query}` — Keyword search across filenames, original filenames, file extensions, and categories.
- `POST /api/documents` — Single file upload (`multipart/form-data`) with MIME/extension validation, SHA-256 duplicate detection, and rule-based categorization.
- `POST /api/documents/batch` — Batch multi-file upload with per-file status reports.
- `GET /api/documents/{id}` — Retrieve document metadata.
- `GET /api/documents/{id}/metadata` — Retrieve extracted structural & cryptographic metadata (hash, size, MIME, extension, upload timestamp, preview capability).
- `PATCH /api/documents/{id}/category` — Manually override document category (sets `is_manually_categorized=True`).
- `GET /api/documents/{id}/preview` — In-browser inline stream preview for PDF, PNG, JPG, and TXT files.
- `GET /api/documents/{id}/download` — Original binary file download with Content-Disposition headers.
- `DELETE /api/documents/{id}` — Permanent, consistent deletion of both database metadata and local storage file.

### Categories
- `GET /api/categories` — List all categories with live aggregated document counts.
- `POST /api/categories` — Create custom category (`name`, `description`, `color`, `icon`).
- `GET /api/categories/{id}` — Retrieve specific category details.
- `PUT /api/categories/{id}` — Update category name, description, or color.
- `DELETE /api/categories/{id}?reassign_to={category}` — Delete category with safe document reassignment (defaulting safely to 'Other').

### Dashboard
- `GET /api/dashboard/statistics` — Real database overview: total documents, storage used bytes & formatted, storage quota percentage, total categories, recent activity count, category distribution, file-type distribution, and recent uploads.

### Activities
- `GET /api/activities` — Chronological audit trail supporting event type filtering (`upload`, `download`, `delete`, `category`), date range filtering (`date_from`, `date_to`, `since`), and keyword search (`q`).

### Settings
- `GET /api/settings` — Retrieve system configuration and profile details.
- `PUT /api/settings` — Update automation preferences, duplicate detection, and profile settings.

---

## 8. AWS Migration Preparation (Phase 2)

Clean, abstract interfaces are established to ensure zero rework of domain logic when deploying to AWS:

### 1. Storage Interface (`backend/storage/base.py`)
```python
class StorageProvider(ABC):
    @abstractmethod
    def save(self, content: bytes, filename: str, subfolder: str = "") -> str: pass

    @abstractmethod
    def get(self, file_path: str) -> bytes: pass

    @abstractmethod
    def delete(self, file_path: str) -> bool: pass

    @abstractmethod
    def generate_download_url(self, file_path: str, expires_in: int = 3600) -> str: pass
```
- **Local Implementation (Phase 1)**: `LocalStorageProvider` writes to disk.
- **AWS Target (Phase 2)**: `S3StorageProvider` uploads to Amazon S3 buckets and returns S3 presigned URLs via Boto3.

### 2. Repository Interface (`backend/repositories/base.py`)
```python
class BaseRepository(ABC, Generic[T]):
    @abstractmethod
    def create(self, entity_data: dict) -> T: pass

    @abstractmethod
    def get(self, entity_id: Any) -> Optional[T]: pass

    @abstractmethod
    def list(self, skip: int = 0, limit: int = 100, **kwargs) -> List[T]: pass

    @abstractmethod
    def update(self, entity_id: Any, update_data: dict) -> Optional[T]: pass

    @abstractmethod
    def delete(self, entity_id: Any) -> bool: pass
```
- **Local Implementation (Phase 1)**: SQLAlchemy with SQLite.
- **AWS Target (Phase 2)**: Boto3 DynamoDB repository or AWS RDS PostgreSQL.

---

## 9. Automated Testing

Run the complete 58-test automated suite using `pytest`:

```powershell
.\venv\Scripts\pytest -v
```

All 58 tests run in isolated environments with automatic teardown and temporary storage cleanup, covering:
- User registration, password hashing (bcrypt), JWT generation, login, `/me` profile retrieval, and unauthorized access rejection.
- Unit and integration tests for all REST API endpoints (`/auth`, `/documents`, `/categories`, `/dashboard`, `/activities`, `/settings`, `/health`).
- Document upload, batch processing, duplicate hashing, preview streaming, and deletion consistency.
- Transparent rule-based categorization heuristics and manual override retention.
- Compound filtering, multi-field search, and 8-mode sorting.
- Category lifecycle protections and document reassignment on deletion.
- Real-time dashboard analytics and chronological audit trail tracking.
- Database and filesystem persistence over application restart cycles.
- Input validation (unsupported formats, oversized files, empty files, missing IDs, malformed requests).
- Security hardening (path traversal elimination, local filesystem path leak prevention, sanitized errors, safe CORS).
