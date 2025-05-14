# DATN_08_2025_Back-end_RAG
 Master: Quách Tấn Dũng

<!-- TABLE OF CONTENTS -->

## Table of Contents

- [Overview](#overview)
- [Server setup and deployment](#server-setup-and-deployment)
  - [Local deployment setup](#local-deployment-setup)
  - [Cloud Run deployment steps](#cloud-run-deployment-steps)
- []
## Overview

- **Purpose:** This is a backend server responsible for receiving PDF files, extracting text and images, and returning the results in JSON format.
- **Technology Stack:** Python, gRPC, Docker, and Google Cloud services (Cloud Run).

## Server setup and deployment

- **Prerequisites:** (Local)
  - Python: version 3.10
  - Dependencies: requirement.txt
- **Prerequisites:** (Google Cloud)
  - Python: version 3.10
  - Dependencies: requirement.txt
  - Docker + WSL
  - Google Cloud account
 
### Local deployment setup
- **Compile proto file:** `python complie_proto.py`
- **Start sever:** `python pdf-grpc-server.py`
- (Optional) **Dev UI:** `python ui.py`

### Cloud Run deployment steps
1. [Install the gcloud GLI](https://cloud.google.com/sdk/docs/install)
2. Login to your Google Cloud acc
   ```bash
   gcloud auth login
   ```
3. Build docker image
   - `LOCATION`: is the regional or multi-regional location of the repository where the image is stored. [I choose the same as when create a new service on Cloud Run (example: asia-southeast1)]
   - `PROJECT-ID`: is your Google Cloud console project ID.
   - `REPOSITORY`: is the name of the repository where the image is stored (Or in my experience is the Artificial Registry in Cloud Run)
   - `IMAGE`: is the image's name. It can be different than the image's local name.
   
   ```bash
   # Yes there is a dot at the end
   docker build -t LOCATION-docker.pkg.dev/PROJECT-ID/REPOSITORY/IMAGE .
   ```
   
4. Push the docker image to Artifact Registry
   ```bash
   docker push LOCATION-docker.pkg.dev/PROJECT-ID/REPOSITORY/IMAGE
   ```
5. Deploy the server:
   - Go to Cloud Run console website.
   - Choose your project.
   - Choose `Deploy container` (choose `Service`).
   - Choose your service name.
   - Choose the server region (I choose same as my Artifact Registry).
   - The other options, i don't have enough knowledge to guide you.
6. Then hit `Create`
   - You should see you service's URL right there, but it take a while for it to finish the setup so be patient.

## Client API guide
- **API Method name**: `ProcessPdf`
  - **Request Format:**:
     - `pdf_data`(bytes base64): PDF file content
     - `filename`(string): Optional name. 
     - **Example**:
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
          "data": {"key": "value"},
          "message": "Success",
          "success": true
      ```
    - **Failture**
      ```json
          "message": "<error_message>",
          "success": false
      ```
 - **API Method name**: "HealthCheck"
    - **Success**
      ```json
          "status": "healthy"
      ```
    - **Failture**
      ```json
          "status": "unhealthy: <error_message>"
      ```
