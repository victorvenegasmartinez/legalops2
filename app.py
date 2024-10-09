import sys,os
sys.path.append(os.getcwd())
print(os.getcwd())
from flask import Flask, jsonify,request
from src.controllers.word_pluging import put_document,answer_question
import logging
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/put/file', methods=['POST'])
def put_file():

    request_json=json.loads(request.data)
    paragraphs=request_json['paragraphs']
    document_id=put_document(paragraphs)

    output=dict()
    output["document_id"]=document_id
    logging.error(output)
    response=jsonify(output)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    logging.error(response)
    return response

@app.route('/get_answer', methods=['POST'])
def get_answer():
    request_json=json.loads(request.data)
    document_id=request_json['document_id']
    query=request_json['query']
    answer=answer_question(query,document_id)
    output=dict()
    output["answer"]=answer
    logging.error(output)
    response=jsonify(output)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    logging.error(response)
    return response

@app.route('/review_contract', methods=['POST'])
def review_contract():
    request_json=json.loads(request.data)
    document_id=request_json['document_id']
    with open('./tests/resources/test.json', 'r') as f:
        data=f.read()
        answer=json.loads(data)
    output=dict()
    output["answer"]=answer
    logging.error(output)
    response=jsonify(output)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    logging.error(response)
    return response


if __name__ == '__main__':
    """flask app"""
    app.run(host="0.0.0.0", port=8000, debug=True)