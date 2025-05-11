FROM continuumio/miniconda3:latest

WORKDIR /app

# Copy environment file first for caching
COPY environment.yml .

# Copy the rest of the files
COPY . .

# Create the Conda environment
RUN conda env create -f environment.yml

# RUN commands use the new environment
SHELL ["conda", "run", "-n", "myenv", "/bin/bash", "-c"]

COPY . .

# Activate environment and run your app
CMD ["conda", "run", "--no-capture-output", "-n", "myenv", "python", "pdf-grpc-server.py"]