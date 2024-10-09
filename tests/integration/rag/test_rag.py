import pytest
import json
import sys,os
sys.path.append(os.getcwd())
from src.controllers.word_pluging import put_document,answer_question,extract_legal_clauses,review_clauses
import logging
import timeit
import json


def read_paragraphs():

    json_path="./tests/resources/input_para.json"

    with open(json_path, 'r') as file:
        data = json.load(file)
    
    return data["paragraphs"]

def test_upload_file():
    """Test to Upload File to retriever"""
    documents = read_paragraphs()
    document_id=put_document(documents)
    logging.info(document_id)

def test_question():
    """test a question"""
    #question="What is this document about?"
    question="What is this document about?"
    response=answer_question(question,"84718265-49d1-4dcf-809f-27c9b75c74f3")
    logging.info(response)

@pytest.mark.asyncio
async def test_extract_review_legal_clause():

    tic=timeit.default_timer()
    documents = read_paragraphs()
    (response_batches,paragraphs,containername)=await extract_legal_clauses(documents)
    response_object,clauses=await review_clauses(response_batches,paragraphs,containername)
    toc=timeit.default_timer()
    elapsed_time=toc - tic
    logging.error(f"elapsed_time:{elapsed_time}")
    response_object=response_object['answer']
    for key in response_object.keys():
        element=response_object[key]
        ids=clauses[key]
        element.update(ids=ids)
        response_object[key]=element

    legal_clauses=[key for key in clauses.keys()]
    with open('./tests/resources/clauses.txt', 'w') as f:
        f.write(' '.join(legal_clauses))

    with open('./tests/resources/test.json', 'w') as f:
        json.dump(response_object, f)

    
    
    logging.info("done")




