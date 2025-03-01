import os
import argparse
import tempfile
from concurrent import futures
from typing import Dict, Any

import grpc
from google.protobuf import empty_pb2
import psycopg2
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv

# Import the PDF processing functionality from main2.py
from extract_pdf import extract_pdf, embed_chunks

# Load environment variables
load_dotenv()

# Define the proto file for our gRPC service
proto_content = """
syntax = "proto3";

package pdf_processor;

service PdfProcessor {
  rpc ProcessPdf(PdfRequest) returns (PdfResponse) {}
  rpc HealthCheck(Empty) returns (HealthCheckResponse) {}
}

message Empty {}

message PdfRequest {
  bytes pdf_data = 1;
  string filename = 2;
}

message PdfResponse {
  int32 chunks_processed = 1;
  string message = 2;
  bool success = 3;
}

message HealthCheckResponse {
  string status = 1;
}
"""

# Write the proto file to disk
with open('pdf_processor.proto', 'w') as f:
    f.write(proto_content)

# Compile the proto file
os.system('python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. pdf_processor.proto')

# Import the generated gRPC modules
import pdf_processor_pb2
import pdf_processor_pb2_grpc

# Constants
MAX_MESSAGE_LENGTH = 100 * 1024 * 1024  # 100MB
DB_CONFIG: Dict[str, str] = {
    'dbname': os.getenv("DB_NAME"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'host': os.getenv("DB_HOST"),
    'port': os.getenv("DB_PORT")
}


class PdfProcessorServicer(pdf_processor_pb2_grpc.PdfProcessorServicer):
    """Implementation of the PdfProcessor service."""

    def ProcessPdf(self, request, context):
        """
        Process a PDF file sent as a byte stream, extract text chunks, and embed them.
        
        Args:
            request: The gRPC request containing the PDF file data
            context: The gRPC context
            
        Returns:
            A PdfResponse message with the processing results
        """
        try:
            # Create a temporary file to store the PDF
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(request.pdf_data)
            
            print(f"Received PDF file: {request.filename}")
            print(f"Saved to temporary file: {temp_file_path}")
            
            # Process the PDF using the existing functionality
            chunks = extract_pdf(temp_file_path)
            print(f"Extracted {len(chunks)} chunks from the PDF")
            
            # Embed the chunks and store in the database
            embed_chunks(chunks)
            print("Embeddings successfully stored in the database")
            
            # Clean up the temporary file
            os.unlink(temp_file_path)
            
            # Return the response
            return pdf_processor_pb2.PdfResponse(
                chunks_processed=len(chunks),
                message=f"Successfully processed {request.filename} and extracted {len(chunks)} chunks",
                success=True
            )
            
        except Exception as e:
            error_message = f"Failed to process PDF: {str(e)}"
            print(error_message)
            return pdf_processor_pb2.PdfResponse(
                chunks_processed=0,
                message=error_message,
                success=False
            )
    
    def HealthCheck(self, request, context):
        """
        Perform a health check to verify the service is running and can connect to the database.
        
        Args:
            request: Empty request
            context: The gRPC context
            
        Returns:
            A HealthCheckResponse with the service status
        """
        try:
            # Test database connection
            with psycopg2.connect(**DB_CONFIG) as conn:
                register_vector(conn)
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            
            return pdf_processor_pb2.HealthCheckResponse(
                status="healthy"
            )
        except Exception as e:
            return pdf_processor_pb2.HealthCheckResponse(
                status=f"unhealthy: {str(e)}"
            )


def verify_db_connection():
    """Verify database connection and required tables exist."""
    try:
        with psycopg2.connect(**DB_CONFIG) as conn:
            register_vector(conn)
            with conn.cursor() as cursor:
                # Check if embeddings table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'embeddings'
                    )
                """)
                table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    # Create the embeddings table with pgvector extension
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    cursor.execute("""
                        CREATE TABLE embeddings (
                            id UUID PRIMARY KEY,
                            doc_fragment TEXT NOT NULL,
                            metadata JSONB,
                            embedding vector(768)
                        )
                    """)
                    print("Created embeddings table")
                else:
                    print("Found existing embeddings table")
            conn.commit()
        return True
    except Exception as e:
        print(f"Database verification failed: {e}")
        return False


def serve(port):
    """Start the gRPC server."""
    # Verify database connection before starting server
    if not verify_db_connection():
        print("Failed to connect to database or create required tables. Exiting.")
        return
    
    # Create a gRPC server with increased message size limit
    server_options = [
        ('grpc.max_send_message_length', MAX_MESSAGE_LENGTH),
        ('grpc.max_receive_message_length', MAX_MESSAGE_LENGTH)
    ]
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=server_options
    )
    
    # Add the service to the server
    pdf_processor_pb2_grpc.add_PdfProcessorServicer_to_server(
        PdfProcessorServicer(), server
    )
    
    # Start the server
    server.add_insecure_port(f'[::]:{port}')
    server.start()
    print(f"Server started on port {port}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("Server shutting down")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="gRPC server for PDF processing")
    parser.add_argument(
        "--port", type=int, default=50051,
        help="Port for the gRPC server (default: 50051)"
    )
    args = parser.parse_args()
    serve(args.port)
