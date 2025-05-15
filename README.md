# DATN_08_2025_Back-end_RAG
 Master: Quách Tấn Dũng

<!-- TABLE OF CONTENTS -->

## Table of Contents

- [Overview](#overview)
- [Server setup and deployment](#server-setup-and-deployment)
  - [Local deployment setup](#local-deployment-setup)
  - [Cloud Run deployment steps](#cloud-run-deployment-steps)
- [Client API guide](#client-api-guide)
## Overview

- **Purpose:** Backend service for extracting text/images from PDFs and returning structured JSON via gRPC.
- **Technology Stack:**
  - Python 3.10, gRPC, Docker
  - Google Cloud (Cloud Run, Artifact Registry)

## Server setup and deployment

- **Prerequisites:**
  - **Local**
    - Python 3.10, `requirement.txt` (`pip install -r requirements.txt`)
  - **Google Cloud**
    - Docker + WSL2 (Windows) / Docker Engine (Linux/macOS)
    - Dependencies: requirement.txt
    - Google Cloud account with billing enabled
    - gcloud CLI ([Install guide](https://cloud.google.com/sdk/docs/install))
 
### Local deployment setup
- **Compile Protobuf:** Generates gRPC stubs
  ```bash
  python compile_proto.py
  ```
- **Start sever:**
  ```bash
  python pdf-grpc-server.py
  ```
- (Optional) **Dev UI:**
  ```bash
  python ui.py
  ```

### Cloud Run deployment steps
**Step 1: Build & Push Docker Image**
   - `LOCATION`: is the regional or multi-regional location of the repository where the image is stored. [I choose the same as when create a new service on Cloud Run (example: asia-southeast1)]
   - `PROJECT-ID`: is your Google Cloud console project ID.
   - `REPOSITORY`: is the name of the repository where the image is stored (Or in my experience is the Artificial Registry in Cloud Run)
   - `IMAGE`: is the image's name. It can be different than the image's local name.
     ```
     # Build image (note the trailing dot)
     docker build -t LOCATION-docker.pkg.dev/PROJECT-ID/REPOSITORY/IMAGE .
     
     # Push to Artifact Registry
     docker push LOCATION-docker.pkg.dev/PROJECT-ID/REPOSITORY/IMAGE
     ```
**Step 2: Deploy to Cloud Run:**
  1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
  2. Click **Create Service → Deploy Container.**
  3. Configure:
     - **Service Name:** `pdf-processor` (or custom).
     - **Region:** Match Artifact Registry (e.g., `asia-southeast1`).
     - **Container Image:** Select the pushed image.
     - **Authentication:** Choose "Allow unauthenticated" (if public).
   4. Click Create.
   5. Wait for the URL (e.g., `https://pdf-processor-xyz.a.run.app`).
 
## Client API guide
- **API Method name:** `ProcessPdf`
  - **gRPC Method:** `pdf_processor.PdfProcessor/ProcessPdf`
  - **Request Format:**
    ```json
    {
       "pdf_data": "<base64_or_binary>",
       "filename": "doc.pdf"
    }
    ```
  - **Respond Format**:
    - **Success**
      - `data`(struct): a JSON like format, contain information extract from the PDF
      ```json
      {
          "data": {"key": "value"},
          "message": "Success",
          "success": true
      }
      ```
    - **Failture**
      ```json
      {
          "message": "<error_message>",
          "success": false
      }
      ```
 - **API Method name:** `HealthCheck`
    - **gRPC Method:** `pdf_processor.PdfProcessor/HealthCheck`
    - **Success**
      ```json
      {
          "status": "healthy"
      }
      ```
    - **Failture**
      ```json
      {
          "status": "unhealthy: <error_message>"
      }
      ```
