# Overview

AI Contract Review is a FastAPI-based web application that provides AI-powered contract analysis and risk assessment. The system allows users to upload contract documents (PDF or DOCX), processes them using OpenAI's GPT-5 model, and provides detailed analysis including risk scores, risky clauses identification, and recommendations for missing protections. The application features a responsive web interface, optional email notifications, and data persistence through Firebase Firestore.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Framework & API Layer
- **FastAPI**: Modern, async web framework chosen for high performance and automatic API documentation
- **Async/Await Pattern**: Used throughout for non-blocking operations, especially for AI analysis and file processing
- **Middleware Stack**: CORS for cross-origin requests and GZip compression for performance optimization
- **Static File Serving**: Direct serving of CSS, JS, and other static assets
- **Template Engine**: Jinja2 for server-side HTML rendering

## Frontend Architecture
- **Vanilla JavaScript**: Simple client-side scripting without heavy frameworks for lightweight performance
- **Bootstrap 5**: CSS framework for responsive UI components and consistent styling
- **Single Page Application**: Dynamic content loading without full page refreshes
- **Progressive Enhancement**: Core functionality works without JavaScript, enhanced with client-side features

## Business Logic Layer
The application follows a service-oriented architecture with clear separation of concerns:

- **FileProcessor Service**: Handles document parsing for PDF (PyPDF2) and DOCX (python-docx) formats
- **AIAnalyzer Service**: Manages OpenAI API integration using GPT-5 model with structured JSON responses
- **FirebaseClient Service**: Handles data persistence and document storage in Firestore
- **NotificationService**: Manages external notifications via n8n webhook integration

## Data Models
- **Pydantic Models**: Used for request/response validation and serialization
- **Structured Analysis Response**: Standardized format for contract analysis results including risk scores, clause analysis, and recommendations
- **Type Safety**: Full typing throughout the codebase for better maintainability

## File Processing Pipeline
1. File upload validation (type and size constraints)
2. Temporary file storage for processing
3. Text extraction based on file type
4. Content validation and preprocessing
5. AI analysis with structured output
6. Result storage and optional notification

## Error Handling & Validation
- **Input Validation**: File type, size, and email format validation
- **Graceful Degradation**: Application continues to function even if Firebase or notifications fail
- **User-Friendly Error Messages**: Clear feedback for validation failures and processing errors

# External Dependencies

## AI/ML Services
- **OpenAI API**: GPT-5 model for contract analysis and risk assessment
- **Model Configuration**: Temperature set to 0.3 for consistent, focused responses
- **Structured Outputs**: JSON response format for reliable data parsing

## Database & Storage
- **Firebase Firestore**: NoSQL document database for storing analysis results and user data
- **Firebase Admin SDK**: Server-side integration for secure database operations
- **Google Cloud Authentication**: Supports both service account keys and default credentials

## File Processing Libraries
- **PyPDF2**: PDF text extraction and processing
- **python-docx**: Microsoft Word document processing
- **Pathlib**: Modern file path handling

## External Integrations
- **n8n Webhooks**: Notification service integration for email alerts and workflow automation
- **Configurable Endpoints**: Environment variable based configuration for different deployment environments

## Frontend Dependencies
- **Bootstrap 5**: CSS framework via CDN
- **Font Awesome 6**: Icon library via CDN
- **No Build Process**: Direct browser-compatible JavaScript and CSS

## Environment Configuration
All external services are configured via environment variables:
- OpenAI API credentials
- Firebase service account and project configuration  
- n8n webhook URLs for notifications
- Base URL configuration for different deployment environments

The architecture prioritizes simplicity, reliability, and clear separation of concerns while maintaining the flexibility to disable optional features (Firebase storage, notifications) without breaking core functionality.