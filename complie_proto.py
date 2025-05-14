import subprocess
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # Define the proto file for our gRPC service
    proto_content = """
    syntax = "proto3";

    package pdf_processor;

    import "google/protobuf/empty.proto";
    import "google/protobuf/struct.proto";

    service PdfProcessor {
        rpc ProcessPdf(PdfRequest) returns (PdfStructResponse) {}
        rpc HealthCheck(google.protobuf.Empty) returns (HealthCheckResponse) {}
    }

    message PdfRequest {
        bytes pdf_data = 1;
        string filename = 2;
    }

    message PdfStructResponse {
        google.protobuf.Struct data = 1;
        string message = 2;
        bool success = 3;
    }

    message HealthCheckResponse {
        string status = 1;
    }
    """

    def compile_proto():
        """Compile the proto file and ensure it succeeds"""
        # Write the proto file to disk
        with open('pdf_processor.proto', 'w') as f:
            f.write(proto_content)
        
        # Compile using subprocess to check for errors
        try:
            result = subprocess.run(
                'python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. pdf_processor.proto',
                shell=True,
                check=True,
                text=True,
                capture_output=True
            )
            logging.info("Proto compilation succeeded")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Proto compilation failed: {e.stderr}")
            return False

    # Compile the proto file
    if not compile_proto():
        logging.error("Failed to compile proto file. Exiting.")
        exit(1)

if __name__ == "__main__":
    main()