from typing import Any, Dict
from abc import ABC, abstractmethod
from collections import defaultdict
from langchain.schema.document import Document
from langchain.text_splitter import SpacyTextSplitter

class DocumentProcessor(ABC):
    "Document Processor"
    @abstractmethod
    def process_document(self, document: Any) -> Any:
        pass

class SpacySplitter(DocumentProcessor,SpacyTextSplitter):
    """Defines an Splitter Using Spacy"""

    def __init__(self):
        self._config = {"chunk_size": 1024,"chunk_overlap": 0}
        super().__init__(**self._config)

    def process_document(self, document: Any) -> Any:

        try:
            doc = self._get_document_wrapper(document)
            # Split the documents into smaller chunks
            chunks = self.split_documents([doc])
            # Add unique (combined) ID and chunk ID to each chunk
            self.add_chunk_ids_to_chunks(chunks)

            return chunks
        except Exception as exc:
            error = "Error when processing input document."
            raise Exception(error)
        
    def add_chunk_ids_to_chunks(self,chunks):
        # Initialize a dictionary to store the chunk ID for each document
        doc_chunk_ids = {}

        # Iterate through the chunks
        for chunk in chunks:
            doc_id = chunk.metadata["doc_id"]

            # Get the current chunk ID for the document or initialize it to 0
            chunk_id = doc_chunk_ids.get(doc_id, 0)

            # Update chunk metadata with chunk ID and combined ID
            chunk.metadata["chunk_id"] = chunk_id
            chunk.metadata["id"] = f"{doc_id}-{chunk_id}"

            # Increment the chunk ID for the current document
            doc_chunk_ids[doc_id] = chunk_id + 1

    def _get_document_wrapper(self,document: Any) -> Document:
        try:

            #TODO we can pass metadata to the Document class
            doc = Document(
                page_content=document['text'],
                metadata={"doc_id":document['doc_id']}
            )
        except Exception:
            error = "Error when creating the Document Wrapper."
            raise Exception(error)

        return doc