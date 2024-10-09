import dspy
import logging

class ContextQASignature(dspy.Signature):

    
    __doc__ =open("./src/prompts/contract_review.txt").read()

    context = dspy.InputField()
    question = dspy.InputField()
    answer = dspy.OutputField(desc="This answer must be in JSON format")


class ExtractLegalClauseSignature(dspy.Signature):

    __doc__ =open("./src/prompts/extract_legal_clause.txt").read()

    question = dspy.InputField()
    answer = dspy.OutputField(desc="This answer must be in XML format")

class ReviewLegalClauseSignature(dspy.Signature):

    __doc__ =open("./src/prompts/review_legal_clause.txt").read()

    question = dspy.InputField()
    answer = dspy.OutputField(desc="This answer must be in XML format")


class RAG(dspy.Module):
    def __init__(self, num_passages=3):
        # Please name your summarization later `summarize` so that we
        # can check for its presence.
        super().__init__()
        self.retrieve = dspy.Retrieve(k=num_passages)

        self.generate_answer = dspy.Predict(ContextQASignature)

    def forward(self, question):
        try:
            passages = self.retrieve(question).passages
            prediction = self.generate_answer(context=passages, question=question)
            return dspy.Prediction(context=passages, answer=prediction.answer)
        except Exception as exc:
            logging.info(exc)
            raise Exception(exc)
        
class ExtractLegalClause(dspy.Module):
    def __init__(self, num_passages=3):
        # Please name your summarization later `summarize` so that we
        # can check for its presence.
        super().__init__()

        self.generate_answer = dspy.Predict(ExtractLegalClauseSignature)

    def forward(self, question):
        try:
            prediction = self.generate_answer(question=question)
            return dspy.Prediction(answer=prediction.answer)
        except Exception as exc:
            logging.info(exc)
            raise Exception(exc)

class ReviewLegalClause(dspy.Module):
    def __init__(self, num_passages=3):
        # Please name your summarization later `summarize` so that we
        # can check for its presence.
        super().__init__()

        self.generate_answer = dspy.Predict(ReviewLegalClauseSignature)

    def forward(self, question):
        try:
            prediction = self.generate_answer(question=question)
            return dspy.Prediction(answer=prediction.answer)
        except Exception as exc:
            logging.info(exc)
            raise Exception(exc)