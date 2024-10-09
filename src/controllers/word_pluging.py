from src.database.mongo_db import MongoDataBase
from src.embeddings.vogayeai import VoyageAI
from src.retrievers.mongodb_retriever import MongoDBRetriever
from src.retrievers.retriever_general import RAG,ExtractLegalClause,ReviewLegalClause
from src.splitter.spacy_splitter import SpacySplitter
from src.azure.blob_storage import AzureBlobStorage
from src.utils.utils_func import InputDataLegalExtractor,InputLegalClause
import logging
import dspy
import os
import json
import uuid
from multiprocessing import Pool
import time
import asyncio
import uuid

MAX_CHUNK_SIZE=15000

def put_document(paragraphs):
    try:
        db = MongoDataBase(os.getenv("ATLAS_DATABASE"),os.getenv("ATLAS_COLLECTION"))
        embeddings=VoyageAI()
        documents=[]
        doc_id=str(uuid.uuid4())

        splitter=SpacySplitter()
        text=[paragraph['text'] for paragraph in paragraphs]

        chunks=splitter.process_document(document={"text":' '.join(text),"doc_id":doc_id})
        texts=[]
        chunkd_ids=[]
        for chunk in chunks:
            texts.append(chunk.page_content)
            chunkd_ids.append(chunk.metadata['chunk_id'])

        doc_emb=embeddings.get_embeddings(documents=texts)
            
        input={"documents":texts,"embeddings":doc_emb,"doc_id":doc_id,"chunk_ids":chunkd_ids}
        document_id=db.save_to_database(input)
        return document_id
    except Exception as exc:
        err="error uploading document to database"
        logging.info(err)
        raise Exception(err)
    
def answer_question(question,document_id):
    try:
        retriever=MongoDBRetriever(document_id)
        lm=dspy.Claude(model=os.getenv("SONNET_MODEL"), api_key=os.getenv("SONNET_API_KEY"))
        dspy.settings.configure(lm=lm, rm=retriever)
        model = RAG()
        pred=model(question)
        response_json={"answer":pred.answer}
        #process_answer(pred.answer)
        return pred.answer
    except Exception:
        err="Error getting answer for a question"
        logging.info(err)
        raise Exception(err)    

def process_answer(answer):
    try:
        json_object=json.loads(answer)

        print(1)
    except Exception:
        err=f"Failed processing answer from model:{answer}"
        logging.error(err)
        raise Exception(err)
    
async def extract_legal_clauses(paragraphs):

    try:

        joined_text=""
        joined_paragraphs=[]

        for paragraph in paragraphs:
            text=paragraph['text']
            text=text.strip()

            joined_text +=text+" \n "

            if text.endswith("."):
                joined_paragraphs.append(joined_text)
                joined_text=""

        batches={}
        current_batch_id=1
        batch_content=[]
        batch_size=0
        paragraphs={}
        for id,text in enumerate(joined_paragraphs):
            batch_size+=len(text)
            paragraphs[(id+1)]=text

            if batch_size>=MAX_CHUNK_SIZE:
                batches[current_batch_id]=batch_content
                current_batch_id+=1
                batch_content=[]
                batch_size=len(text)
            
            batch_content.append({"id":(id+1),"text":text})
        
        if len(batch_content)>0:
            batches[current_batch_id]=batch_content
            batch_content=[]
            current_batch_id=-1
            batch_size=0
        
        #legal_clause_extractor = ExtractLegalClause()
        response_batches={}
        results=[]
        containername=str(uuid.uuid4())
        with Pool(processes=10) as pool:
            for key in batches:
                xml_request="<body>"
                batch_content=batches[key]
                for element in batch_content:
                    item="<item>"
                    item+="<id>"+str(element["id"])+"</id>"
                    item+="<text>"+element["text"]+"</text>"
                    item+="</item>"
                    xml_request+=item
                xml_request+="</body>"
                input_data=InputDataLegalExtractor(xml_request,containername)
                result=pool.apply_async(run_call_llm,(input_data,))
                results.append(result)
            pool.close()
            pool.join()
                #tasks.append( asyncio.create_task(call_llm(xml_request)),)
            #xml_response=legal_clause_extractor(xml_request)

            #response_batches=read_cluses(xml_response.answer,response_batches)
        #results=await asyncio.gather(*tasks)

        while True:
            time.sleep(1)
            # catch exception if results are not ready yet
            try:
                ready = [result.ready() for result in results]
                successful = [result.successful() for result in results]
            except Exception:
                continue
            # exit loop if all tasks returned success
            if all(successful):
                break
            # raise exception reporting exceptions received from workers
            if all(ready) and not all(successful):
                exceptions = [result._value for result in results if not result.successful()]
                raise Exception(f'Workers raised following exceptions {exceptions}')

        #containername="e7576106-2152-4f5d-ae9c-ba10ab4a9a49"
        root_container=os.getenv("LEGAL_EXTRACTOR_CONTAINER")
        blob_handler=AzureBlobStorage(containername,root_container)
        blob_list= blob_handler.list_blobs()
        index=0

        for blob in blob_list:
            blob_stream=blob_handler.download_blob(blob)
            json_object=json.loads(blob_stream)
            if index==0:
                response_batches=json_object
            else:
                dictionary_clauses=json_object
                for clause in dictionary_clauses.keys():
                    ids=dictionary_clauses.get(clause)
                    if clause in response_batches and len(clause)>0:
                        obj_ids=response_batches.get(clause)
                        obj_ids.append(ids)
                        response_batches[clause]=obj_ids
                    else:
                        response_batches[clause]=ids
            index=index+1

        return (response_batches,paragraphs,containername)
    except Exception as exc:
        err="Error Extracting legal clauses from contract"
        raise Exception(err)
    
def run_call_llm(input_data:InputDataLegalExtractor):
    asyncio.run(call_llm(input_data,))

async def call_llm(input_data:InputDataLegalExtractor):
    try:
        xml_request=input_data.xml_request
        containername=input_data.container_name

        lm=dspy.Claude(model=os.getenv("SONNET_MODEL"), api_key=os.getenv("SONNET_API_KEY"))
        dspy.settings.configure(lm=lm)
        legal_clause_extractor = ExtractLegalClause()
        xml_response=legal_clause_extractor(xml_request)
        response_batches=read_cluses(xml_response.answer)
        data=json.dumps(response_batches)
        #data=json.dumps({"test":"test"})
        root_container=os.getenv("LEGAL_EXTRACTOR_CONTAINER")
        blob_storage=AzureBlobStorage(containername,root_container)
        blobname=str(uuid.uuid4())
        blob_storage.upload_blob_file(blobname=blobname,data=data)
    except Exception as exc:
        err=exc
        raise Exception(err)
    
def return_clauses(response_batches,paragraphs):
    clauses=[]
    for key in response_batches:
        if len(key)==0:
            continue

        ids=response_batches[key]
        if len(ids)>0:
            clause_name=key

            clause=[paragraphs.get(int(id)) for id in ids]
            clause= ' '.join(clause)
            clause=clause_name+":"+clause
            clauses.append({"clause":clause,"ids":ids})
    return clauses
    
async def review_clauses(response_batches,paragraphs,containername):
    try:
        #lm=dspy.Claude(model=os.getenv("SONNET_MODEL"), api_key=os.getenv("SONNET_API_KEY"))
        #dspy.settings.configure(lm=lm)
        #legal_clause_reviewer = ReviewLegalClause()
        response_json={}
        clauses={}
        results=[]
        with Pool(processes=10) as pool:
            for key in response_batches:
                if len(key)==0:
                    continue

                ids=response_batches[key]
                if len(ids)>0:
                    clause_name=key

                    clause=[paragraphs.get(int(id)) for id in ids]
                    clause= ' '.join(clause)
                    clauses[clause_name]=ids
                    prompt="This is a "+clause_name+" legal clause; the text of this clause is the following:"+clause
                    input_data=InputLegalClause(prompt,clause_name,containername)
                    result=pool.apply_async(run_llm_review_clause,(input_data,))
                    results.append(result)
                #tasks.append( asyncio.create_task(llm_review_clause(prompt,clause_name)),)
            pool.close()
            pool.join()

                #response=legal_clause_reviewer(clause)
        #results=await asyncio.gather(*tasks)

        while True:
            time.sleep(1)
            # catch exception if results are not ready yet
            try:
                ready = [result.ready() for result in results]
                successful = [result.successful() for result in results]
            except Exception:
                continue
            # exit loop if all tasks returned success
            if all(successful):
                break
            # raise exception reporting exceptions received from workers
            if all(ready) and not all(successful):
                exceptions = [result._value for result in results if not result.successful()]
                raise Exception(f'Workers raised following exceptions {exceptions}')
            
        root_container=os.getenv("LEGAL_REVIEW_CLAUSE_CONTAINER")
        blob_handler=AzureBlobStorage(containername,root_container)
        blob_list= blob_handler.list_blobs()

        for blob in blob_list:
            blob_stream=blob_handler.download_blob(blob)
            result=json.loads(blob_stream)
            response_json[result["clause_name"]]=result
        #for result in results:
            #response_json[result["clause"]]=result["json"]

                #response_json=read_review_clause(response.answer,response_json,clause_name)
        return {"answer":response_json},clauses
    except Exception:
        err="Error Reviewing Single Clauses"
        raise Exception(err)

def run_llm_review_clause(input_data:InputLegalClause):
    asyncio.run(llm_review_clause(input_data,))
    

async def llm_review_clause(input_data:InputLegalClause):
    try:
        lm=dspy.Claude(model=os.getenv("SONNET_MODEL"), api_key=os.getenv("SONNET_API_KEY"))
        dspy.settings.configure(lm=lm)

        prompt=input_data.prompt
        clause_name=input_data.clause_name
        containername=input_data.containername
        legal_clause_reviewer = ReviewLegalClause()
        response=legal_clause_reviewer(prompt)
        response_json=read_review_clause(response.answer,clause_name)
        #return {"clause":clause_name,"json":response_json}
        data=json.dumps(response_json)
        root_container=os.getenv("LEGAL_REVIEW_CLAUSE_CONTAINER")
        blob_storage=AzureBlobStorage(containername,root_container)
        blobname=str(uuid.uuid4())
        blob_storage.upload_blob_file(blobname=blobname,data=data)

    except Exception as exc:
        err="Error Reviewing Clause"
        raise Exception(err)
            
def read_review_clause(xml_string,clause_name):

    open_tag="<review>"
    close_tag="</review>"
    start = xml_string.find(open_tag)
    end = xml_string.find(close_tag)
    review = xml_string[start + len(open_tag):end]
    
    start = review.find("<missing>")
    end = review.find("</missing>")
    missing_information = review[start + len("<missing>"):end]

    start = review.find("<obligations>")
    end = review.find("</obligations>")
    obligations = review[start + len("<obligations>"):end]

    start = review.find("<benefits>")
    end = review.find("</benefits>")
    benefits = review[start + len("<benefits>"):end]

    start = review.find("<dates>")
    end = review.find("</dates>")
    dates = review[start + len("<dates>"):end]

    start = review.find("<risk>")
    end = review.find("</risk>")
    risk = review[start + len("<risk>"):end]

    start = review.find("<key-terms>")
    end = review.find("</key-terms>")
    key_term = review[start + len("<key-terms>"):end]

    start = review.find("<recommendations>")
    end = review.find("</recommendations>")
    recommendations = review[start + len("<recommendations>"):end]

    return {"missing_information":missing_information,"obligations":obligations,"benefits":benefits,
                                "dates":dates,"risk":risk,"key_term":key_term,"recommendations":recommendations,
                                "clause_name":clause_name}


def read_cluses(xml_string,):

    try:
        response_batches={}
        open_tag="<answer>"
        close_tag="</answer>"
        start = xml_string.find(open_tag)
        end = xml_string.find(close_tag)
        clauses = xml_string[start + len(open_tag):end]
        len_clauses=len(clauses)
        
        while len_clauses>0:
            start = clauses.find("<clause>")
            end = clauses.find("</clause>")
            clause = clauses[start + len("<clause>"):end]
            hstart=clause.find("<h1>")
            hend=clause.find("</h1>")
            clause_name=clause[hstart + len("<h1>"):hend]
            idsstart=clause.find("<ids>")
            idsend=clause.find("</ids>")
            ids_str=clause[idsstart + len("<ids>"):idsend]
            ids=ids_str.split(",")
            clauses=clauses[len("</clause>")+end:]
            len_clauses=len(clauses)
            if clause_name in response_batches and len(clause_name)>0:
                obj_ids=response_batches.get(clause_name)
                obj_ids.append(ids)
                response_batches[clause_name]=obj_ids
            else:
                response_batches[clause_name]=ids
        return response_batches
    except Exception:
        err="Error reading xml response"
        raise Exception(err)


