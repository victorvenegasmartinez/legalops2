class InputDataLegalExtractor(object):

    def __init__(self,xml_request,container_name):
        self.xml_request=xml_request
        self.container_name=container_name

class InputLegalClause(object):

    def __init__(self,prompt,clause_name,containername):
        self.prompt=prompt
        self.clause_name=clause_name
        self.containername=containername

