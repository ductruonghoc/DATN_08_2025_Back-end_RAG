from pathlib import Path
import json
import sys
import logging
import tempfile
from docling_core.types.doc import PictureItem, TableItem
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    AcceleratorDevice,
    AcceleratorOptions,
    PdfPipelineOptions
)
from docling.document_converter import DocumentConverter as DoclingDocumentConverter, PdfFormatOption

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class DocumentProcessor:
    def __init__(self):
        self.converter = self._init_converter()
        self.logger = logger
        
    def _init_converter(self):
        """Initialize the document converter with pipeline options"""
        accelerator_options = AcceleratorOptions(
            num_threads=8, 
            device=AcceleratorDevice.AUTO
        )

        pipeline_options = PdfPipelineOptions(
            accelerator_options=accelerator_options,
            images_scale=2.0,
            generate_picture_images=True,
            generate_page_images = True,
        )

        return DoclingDocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
    
    def process_images_tables(self, conv_res, output_dir: str) -> None:
        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            table_counter = 0
            picture_counter = 0
            for element, _level in conv_res.document.iterate_items():
                if isinstance(element, (TableItem, PictureItem)):
                    if isinstance(element, TableItem):
                        table_counter += 1
                        logger.info(f"Processing table {table_counter}")
                        element_image_filename = (
                            output_dir / f"table-{table_counter}.png"
                        )
                        with element_image_filename.open("wb") as fp:
                            element.get_image(conv_res.document).save(fp, "PNG")
                    else:
                        picture_counter += 1
                        logger.info(f"Processing picture {picture_counter}")
                        element_image_filename = (
                            output_dir / f"picture-{picture_counter}.png"
                        )
                        with element_image_filename.open("wb") as fp:
                            element.get_image(conv_res.document).save(fp, "PNG")
        except Exception as e:
            logger.error(f"Error processing images and tables: {e}", exc_info=True)
            raise

    def process(self, pdf_path: str, output_dir: str) -> None:
        """Public method to handle PDF processing"""
        try:
            self.logger.info("Processing PDF file...")
            conv_res = self.converter.convert(
                pdf_path,
                # max_num_pages=100,
                # max_file_size=20971520
            )
            self.logger.info("PDF conversion completed successfully.")

            if conv_res.document is None:
                self.logger.error("Conversion result is None")
                return None
            else:
                self.logger.info(f"Extracting images and tables to {output_dir}")
                self.process_images_tables(conv_res, output_dir)

            return (
                conv_res.document.export_to_dict()
            )
        except Exception as e:
            self.logger.critical(f"Unhandled exception in main process: {e}", exc_info=True)
            sys.exit(1)

if __name__ == "__main__":
    # Example usage
    processor = DocumentProcessor()
    processor.process("path/to/your/file.pdf")