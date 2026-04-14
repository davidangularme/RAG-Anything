import logging
from typing import Dict, List, Optional, Union
import io
from pathlib import Path

from mineru import MinerU
from mineru.error import MinerUError

logger = logging.getLogger(__name__)


class PDFParser:
    """PDF parser using MinerU library."""

    def __init__(self, parser: str = "auto"):
        """Initialize PDF parser.

        Args:
            parser: Parser type ("auto", "pypdfium2", "paddleocr", "pdfplumber", "fitz")
        """
        self.parser = parser
        self.mineru = MinerU()

    def parse(self, pdf_path: Union[str, Path, io.BytesIO]) -> Dict:
        """Parse PDF file.

        Args:
            pdf_path: Path to PDF file or BytesIO object

        Returns:
            Dictionary containing parsed content

        Raises:
            ValueError: If PDF file is corrupted or cannot be parsed
            FileNotFoundError: If PDF file does not exist
            IOError: If there is an I/O error reading the file
        """
        try:
            # Handle different input types
            if isinstance(pdf_path, (str, Path)):
                pdf_path = Path(pdf_path)
                if not pdf_path.exists():
                    raise FileNotFoundError(f"PDF file not found: {pdf_path}")
                
                # Check if file is empty
                if pdf_path.stat().st_size == 0:
                    raise ValueError(f"PDF file is empty: {pdf_path}")
                
                # Try to read file to check if it's accessible
                try:
                    with open(pdf_path, 'rb') as f:
                        # Read first few bytes to check if it's a PDF
                        header = f.read(5)
                        if header != b'%PDF-' and header != b'%FDF-' and header != b'%EOF':
                            # Not a standard PDF header, but might still be parseable
                            logger.warning(f"File {pdf_path} does not have standard PDF header")
                except IOError as e:
                    raise IOError(f"Cannot read PDF file {pdf_path}: {str(e)}")
                
                logger.info(f"Parsing PDF file: {pdf_path}")
                result = self.mineru.parse(str(pdf_path), parser=self.parser)
            elif isinstance(pdf_path, io.BytesIO):
                logger.info("Parsing PDF from BytesIO")
                # Save BytesIO content to temporary file for parsing
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                    tmp_file.write(pdf_path.getvalue())
                    tmp_path = tmp_file.name
                
                try:
                    result = self.mineru.parse(tmp_path, parser=self.parser)
                finally:
                    # Clean up temporary file
                    import os
                    os.unlink(tmp_path)
            else:
                raise ValueError(f"Unsupported input type: {type(pdf_path)}")
            
            return result
            
        except MinerUError as e:
            error_msg = f"Failed to parse PDF: {str(e)}"
            logger.error(error_msg)
            
            # Provide more specific error messages for common issues
            if "corrupt" in str(e).lower() or "damaged" in str(e).lower():
                raise ValueError(f"PDF file appears to be corrupted or damaged: {str(e)}")
            elif "password" in str(e).lower():
                raise ValueError(f"PDF file is password protected: {str(e)}")
            elif "not a pdf" in str(e).lower():
                raise ValueError(f"File is not a valid PDF: {str(e)}")
            else:
                raise ValueError(error_msg)
                
        except FileNotFoundError as e:
            logger.error(f"PDF file not found: {str(e)}")
            raise
            
        except IOError as e:
            logger.error(f"I/O error reading PDF file: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error parsing PDF: {str(e)}")
            raise ValueError(f"Failed to parse PDF due to unexpected error: {str(e)}")

    def extract_text(self, pdf_path: Union[str, Path, io.BytesIO]) -> str:
        """Extract text from PDF file.

        Args:
            pdf_path: Path to PDF file or BytesIO object

        Returns:
            Extracted text as string

        Raises:
            ValueError: If PDF file is corrupted or cannot be parsed
            FileNotFoundError: If PDF file does not exist
            IOError: If there is an I/O error reading the file
        """
        try:
            result = self.parse(pdf_path)
            
            # Extract text from all pages
            text_parts = []
            for page in result.get("pages", []):
                page_text = page.get("text", "")
                if page_text:
                    text_parts.append(page_text)
            
            full_text = "\n\n".join(text_parts)
            
            # Check if any text was extracted
            if not full_text.strip():
                logger.warning("No text content extracted from PDF")
                
            return full_text
            
        except Exception as e:
            # Re-raise the exception with appropriate message
            if isinstance(e, (ValueError, FileNotFoundError, IOError)):
                raise
            else:
                raise ValueError(f"Failed to extract text from PDF: {str(e)}")

    def extract_metadata(self, pdf_path: Union[str, Path, io.BytesIO]) -> Dict:
        """Extract metadata from PDF file.

        Args:
            pdf_path: Path to PDF file or BytesIO object

        Returns:
            Dictionary containing PDF metadata

        Raises:
            ValueError: If PDF file is corrupted or cannot be parsed
            FileNotFoundError: If PDF file does not exist
            IOError: If there is an I/O error reading the file
        """
        try:
            result = self.parse(pdf_path)
            return result.get("metadata", {})
            
        except Exception as e:
            # Re-raise the exception with appropriate message
            if isinstance(e, (ValueError, FileNotFoundError, IOError)):
                raise
            else:
                raise ValueError(f"Failed to extract metadata from PDF: {str(e)}")

    def extract_images(self, pdf_path: Union[str, Path, io.BytesIO]) -> List[Dict]:
        """Extract images from PDF file.

        Args:
            pdf_path: Path to PDF file or BytesIO object

        Returns:
            List of dictionaries containing image data

        Raises:
            ValueError: If PDF file is corrupted or cannot be parsed
            FileNotFoundError: If PDF file does not exist
            IOError: If there is an I/O error reading the file
        """
        try:
            result = self.parse(pdf_path)
            
            images = []
            for page in result.get("pages", []):
                page_images = page.get("images", [])
                images.extend(page_images)
            
            return images
            
        except Exception as e:
            # Re-raise the exception with appropriate message
            if isinstance(e, (ValueError, FileNotFoundError, IOError)):
                raise
            else:
                raise ValueError(f"Failed to extract images from PDF: {str(e)}")

    def validate_pdf(self, pdf_path: Union[str, Path]) -> bool:
        """Validate if a file is a valid PDF.

        Args:
            pdf_path: Path to PDF file

        Returns:
            True if file is a valid PDF, False otherwise
        """
        try:
            pdf_path = Path(pdf_path)
            
            # Basic file checks
            if not pdf_path.exists():
                logger.error(f"File does not exist: {pdf_path}")
                return False
                
            if pdf_path.stat().st_size == 0:
                logger.error(f"File is empty: {pdf_path}")
                return False
            
            # Check PDF header
            try:
                with open(pdf_path, 'rb') as f:
                    header = f.read(5)
                    # Check for PDF header (PDF 1.0-1.7) or FDF header
                    if header not in [b'%PDF-', b'%FDF-', b'%EOF']:
                        # Some PDFs might not start with standard header
                        # Try to read more to check for PDF magic number
                        f.seek(0)
                        content = f.read(1024)
                        if b'%PDF' not in content and b'%FDF' not in content:
                            logger.warning(f"File does not appear to be a PDF: {pdf_path}")
                            return False
            except IOError as e:
                logger.error(f"Cannot read file: {pdf_path}, error: {str(e)}")
                return False
            
            # Try to parse a small part of the PDF
            try:
                # Parse just the first page to validate
                result = self.mineru.parse(str(pdf_path), parser=self.parser, pages=[0])
                if result and "pages" in result:
                    return True
                else:
                    logger.warning(f"PDF parsing returned empty result: {pdf_path}")
                    return False
                    
            except MinerUError as e:
                logger.warning(f"PDF validation failed: {pdf_path}, error: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error during PDF validation: {pdf_path}, error: {str(e)}")
            return False