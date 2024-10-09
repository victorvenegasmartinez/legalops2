from pymongo import InsertOne
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os
import uuid
import logging

URI=os.getenv("LEGAL_OPS_MONGODB")
EMBEDDING_FIELD_NAME="sentence_embedding"
ATLAS_VECTOR_SEARCH_INDEX_NAME=os.getenv("ATLAS_VECTOR_SEARCH_INDEX_NAME")

class MongoDataBase(object):

    def __init__(self,database,collection):
        # Create a new client and connect to the server
        self.client = MongoClient(URI, server_api=ServerApi('1'))
        # Send a ping to confirm a successful connection
        try:
            self.client.admin.command('ping')
            logging.info("Pinged your deployment. You successfully connected to MongoDB!")
            self.db = self.client.get_database(database)
            self.db_collection=self.get_collection(collection)
        except Exception:
            err="Error Connecting to the Database"
            logging.error(err)
            raise Exception(err)

    def get_collection(self,collection:str):
        return self.db.get_collection(collection)
    
    def extract_time(self,json):
        try:
            # Also convert to int since update_time will be string.  When comparing
            # strings, "10" is smaller than "2".
            return int(json['start_offset'])
        except KeyError:
            return 0
        
    def save_to_database(self,input):
        """Save to Database"""

        documents=input['documents']
        documents_embds=input['embeddings']
        chunk_ids=input['chunk_ids']
        id=input['doc_id']

        requests=[]
        start_offset=0
        end_offset=0
        
        for document,embedding,chunk_id in zip(documents,documents_embds,chunk_ids):
            end_offset=start_offset+len(document)
            mongo_document={EMBEDDING_FIELD_NAME:embedding,"Document":document,"document_id":id,
                            "start_offset":start_offset,"end_offset":end_offset,"chunk_ids":chunk_id}
            requests.append(InsertOne( mongo_document))
            start_offset=end_offset
        result=self.db_collection.bulk_write(requests)
        return id
    
    def knn_search(self,query_vectors,document_id):

        results=[]
        for vector in query_vectors:
            result = self.db_collection.aggregate([
            {
                '$vectorSearch': {
                    "index": ATLAS_VECTOR_SEARCH_INDEX_NAME,
                    "path": EMBEDDING_FIELD_NAME,
                    "queryVector": vector,
                    "numCandidates": 150,
                    "limit": 10,
                    "filter": {"document_id": {"$eq": document_id}}
                }
            },
            {
                "$addFields": {"score": {"$meta": "vectorSearchScore"}}
            },
            {
                "$project": {"vector": 0}
            },
            ])

            for sentence in result:
                results.append({"Document":sentence['Document'],"start_offset":sentence['start_offset'],"end_offset":sentence['end_offset'],"chunk_ids":sentence['chunk_ids']})
            
        return results

