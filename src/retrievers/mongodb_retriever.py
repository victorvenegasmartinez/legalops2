
from typing import Optional
from src.database.mongo_db import MongoDataBase
from src.embeddings.vogayeai import VoyageAI
import dspy
import os

class Passage(object):
    def __init__(self,long_text):
        self.long_text=long_text

class MongoDBRetriever(dspy.Retrieve):
    """MongoDB Retriever"""
    def __init__(self,document_id):
        self.db=MongoDataBase(os.getenv("ATLAS_DATABASE"),os.getenv("ATLAS_COLLECTION"))
        self.embeddings=VoyageAI()
        self.document_id=document_id
        self.responses=[]

    def forward(self, query_or_queries:str, k:Optional[int]) -> dspy.Prediction:
        # Only accept single query input, feel free to modify it to support 
        query_embedding=self.embeddings.get_embeddings([query_or_queries])
        query_len=len(query_embedding[0])
        print(query_embedding[0])
        response=self.db.knn_search(query_embedding,self.document_id)
        self.responses.append(response)
        number_of_document=1
        passages=[]
        for document in response:
            passages.append("Document Number "+str(number_of_document)+": "+document['Document'])
            number_of_document+=1
        
        passage=Passage(' '.join(passages))

        return passage


