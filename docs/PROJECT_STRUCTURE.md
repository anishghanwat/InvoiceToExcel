# Project Structure

## Overview
This document outlines the project structure for the Invoice to CSV conversion tool, designed for scalability and maintainability.

## Current Structure

```
InvoiceToExcel/
├── src/
│   ├── core/                    # Core business logic
│   │   ├── __init__.py
│   │   ├── extraction/          # Document extraction layer
│   │   │   ├── __init__.py
│   │   │   ├── textract_client.py
│   │   │   └── document_processor.py
│   │   ├── normalization/       # Data normalization layer (future)
│   │   │   ├── __init__.py
│   │   │   ├── data_normalizer.py
│   │   │   ├── field_mapper.py
│   │   │   └── validation.py
│   │   ├── mapping/             # CSV mapping layer
│   │   │   ├── __init__.py
│   │   │   ├── csv_mapper.py
│   │   │   └── column_matcher.py
│   │   └── export/              # Export functionality
│   │       ├── __init__.py
│   │       ├── csv_exporter.py
│   │       └── excel_exporter.py
│   ├── interfaces/              # User interfaces
│   │   ├── __init__.py
│   │   ├── cli.py
│   │   ├── interactive_csv.py
│   │   └── web_interface.py     # Future web UI
│   ├── utils/                   # Utility functions
│   │   ├── __init__.py
│   │   ├── file_utils.py
│   │   ├── config.py
│   │   └── logger.py
│   └── models/                  # Data models
│       ├── __init__.py
│       ├── document.py
│       ├── extraction_result.py
│       └── csv_config.py
├── tests/                       # Test files
│   ├── __init__.py
│   ├── test_extraction/
│   ├── test_normalization/
│   ├── test_mapping/
│   └── test_export/
├── config/                      # Configuration files
│   ├── __init__.py
│   ├── settings.py
│   └── field_mappings.json
├── docs/                        # Documentation
│   ├── API.md
│   ├── SETUP.md
│   └── EXAMPLES.md
├── output/                      # Generated output files
├── samples/                     # Sample documents for testing
├── .env.example                 # Environment template
├── .gitignore
├── requirements.txt
├── setup.py                     # Package setup
└── README.md
```

## Layer Responsibilities

### 1. Extraction Layer (`src/core/extraction/`)
- **Purpose**: Extract raw data from documents
- **Components**:
  - `textract_client.py`: AWS Textract integration
  - `document_processor.py`: Main extraction workflow

### 2. Normalization Layer (`src/core/normalization/`)
- **Purpose**: Clean, validate, and normalize extracted data
- **Components**:
  - `data_normalizer.py`: Main normalization logic
  - `field_mapper.py`: Map raw fields to standard formats
  - `validation.py`: Data validation rules

### 3. Mapping Layer (`src/core/mapping/`)
- **Purpose**: Map normalized data to user-defined CSV columns
- **Components**:
  - `csv_mapper.py`: Main mapping logic
  - `column_matcher.py`: Intelligent column matching

### 4. Export Layer (`src/core/export/`)
- **Purpose**: Export data to various formats
- **Components**:
  - `csv_exporter.py`: CSV export functionality
  - `excel_exporter.py`: Excel export functionality

### 5. Interface Layer (`src/interfaces/`)
- **Purpose**: User interaction interfaces
- **Components**:
  - `cli.py`: Command line interface
  - `interactive_csv.py`: Interactive CSV creator
  - `web_interface.py`: Future web UI

### 6. Models Layer (`src/models/`)
- **Purpose**: Data structures and models
- **Components**:
  - `document.py`: Document model
  - `extraction_result.py`: Extraction result model
  - `csv_config.py`: CSV configuration model

### 7. Utils Layer (`src/utils/`)
- **Purpose**: Shared utilities and helpers
- **Components**:
  - `file_utils.py`: File operations
  - `config.py`: Configuration management
  - `logger.py`: Logging utilities

## Data Flow

```
Document Input
     ↓
[Extraction Layer] → Raw extracted data
     ↓
[Normalization Layer] → Clean, validated data
     ↓
[Mapping Layer] → Column-mapped data
     ↓
[Export Layer] → CSV/Excel output
```

## Future Extensions

This structure allows for easy addition of:
- Multiple extraction engines (OCR alternatives)
- Advanced normalization rules
- Machine learning-based field detection
- Multiple export formats
- Web interface
- API endpoints
- Batch processing
- Template management

## Benefits

1. **Separation of Concerns**: Each layer has a single responsibility
2. **Scalability**: Easy to add new features without affecting existing code
3. **Testability**: Each component can be tested independently
4. **Maintainability**: Clear structure makes code easy to understand and modify
5. **Extensibility**: New functionality can be added without major refactoring