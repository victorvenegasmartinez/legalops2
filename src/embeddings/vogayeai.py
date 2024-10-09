from langchain_voyageai import VoyageAIEmbeddings
import os
import logging

class VoyageAI(object):

    def __init__(self):
        self.embeddings = VoyageAIEmbeddings(voyage_api_key=os.getenv("VOYAGE_API_KEY"), model=os.getenv("VOYAGE_MODEL"))

    def get_embeddings(self,documents:list):
        """get en¿mbeddings for a document"""
        try:
            documents_embds = self.embeddings.embed_documents(documents)
            return documents_embds
        except Exception:
            err="Error when getting embeddings"
            logging.info(err)
            raise Exception(err)
            