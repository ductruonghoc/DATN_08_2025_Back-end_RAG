import os
import shutil
import argparse
import tempfile
from concurrent import futures
from typing import Dict, Any
import json

import grpc
from google.protobuf import json_format, empty_pb2
from google.protobuf.struct_pb2 import Struct
from dotenv import load_dotenv

import logging
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Load environment variables
load_dotenv()

# Import the generated gRPC modules
import pdf_processor_pb2
import pdf_processor_pb2_grpcW

# Constants
MAX_MESSAGE_LENGTH = 100 * 1024 * 1024  # 100MB

class PdfProcessorServicer(pdf_processor_pb2_grpc.PdfProcessorServicer):
    """Implementation of the PdfProcessor service."""
    def ProcessPdf(self, request, context):
        """Process PDF and return structured data response"""
        logging.info(f"Processing PDF: {request.filename}")
        try:
            from extract_pdf import DocumentProcessor
            
            # Create and write to temporary file
            logging.info("Creating temporary file for PDF data")
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(request.pdf_data)
                temp_file_path = temp_file.name

            logging.info(f"Creating temporary image directory for images")
            temp_image_path = tempfile.mkdtemp(suffix='_images')
            
            logging.info(f"PDF saved to temporary file: {temp_file_path}")
            logging.info(f"Temporary image directory: {temp_image_path}")
            # Process the PDF
            processor = DocumentProcessor()
            dict_result = processor.process(temp_file_path, temp_image_path)
            
            # Validate result
            if dict_result is None:
                error_message = "Processing returned None result"
                logging.error(error_message)
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details(error_message)
                return pdf_processor_pb2.PdfStructResponse(
                    message=error_message,
                    success=False
                )
            
            # Log the structure for debugging
            logging.debug(f"Processing result structure: {type(dict_result)}")
            
            # Convert Python dict to Protobuf Struct
            struct_data = Struct()
            json_format.ParseDict(dict_result, struct_data)
            
            logging.info(f"Successfully processed {request.filename}")
            return pdf_processor_pb2.PdfStructResponse(
                data=struct_data,
                message=f"Successfully processed {request.filename}",
                success=True
            )
            
        except json_format.ParseError as e:
            error_message = f"Error converting data to Protobuf: {str(e)}"
            logging.error(error_message)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(error_message)
            return pdf_processor_pb2.PdfStructResponse(
                message=error_message,
                success=False
            )
        except Exception as e:
            error_message = f"Failed to process PDF: {str(e)}"
            logging.error(error_message)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(error_message)
            return pdf_processor_pb2.PdfStructResponse(
                message=error_message,
                success=False
            )
        finally:
             if temp_file_path:
                try:
                    os.unlink(temp_file_path)
                    shutil.rmtree(temp_image_path)
                except OSError as e:
                    logging.error(f"Error deleting temp file: {e}")
            
    def HealthCheck(self, request, context):
        logging.info("Health check requested")
        try:
            return pdf_processor_pb2.HealthCheckResponse(
                status="healthy"
            )
        except Exception as e:
            error_message = f"Error in health check: {str(e)}"
            logging.error(error_message)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(error_message)
            return pdf_processor_pb2.HealthCheckResponse(
                status=f"unhealthy: {str(e)}"
            )

def serve(port):
    """Start the gRPC server."""
    
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
    logging.info(f"Server started on port {port}")
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logging.info("Server shutting down")
        server.stop(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="gRPC server for PDF processing")
    parser.add_argument(
        "--port", type=int, default=50051,
        help="Port for the gRPC server (default: 50051)"
    )
    args = parser.parse_args()
    serve(args.port)