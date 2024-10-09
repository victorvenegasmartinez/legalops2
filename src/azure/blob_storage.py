import io
import os
import uuid
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, generate_account_sas, ResourceTypes, AccountSasPermissions
from azure.identity import DefaultAzureCredential
import json



class AzureBlobStorage(object):

    def __init__(self,containername,legal_container):

        credential=DefaultAzureCredential()
        url=os.getenv("LEGALOPS_CONTAINER_URL")
        self.blob_client=BlobServiceClient(account_url=url, credential=credential,)
        self.containername=containername
        self.legal_container=legal_container
        container_client = self.blob_client.get_container_client(container=self.legal_container)
        if not container_client.exists():
            container_client.create_container()

    def upload_blob_file(self,blobname:str,data:str):
        try:
            container_client = self.blob_client.get_container_client(container=self.legal_container)
            blobname=f"{self.containername}/{blobname}"
            container_client.upload_blob(name=blobname, data=data, overwrite=True)
        except Exception as exc:
            err="Error uploading file to blob"
            raise Exception(err)
        
    def download_blob(self,blob_name):
        try:
            blob_client = self.blob_client.get_blob_client(container=self.legal_container, blob= blob_name)
            download_stream = blob_client.download_blob()
            content=download_stream.readall()
            content = content.decode("utf-8")
            return content
        except Exception:
            err="Error uploading file to blob in Azure"
            raise Exception(err)

    def list_blobs(self,):
        try:
            blob_list = []
            container_client = self.blob_client.get_container_client(container=self.legal_container)
            root_path=self.containername
            for blob in container_client.list_blobs():
                if blob['name'].startswith(root_path):
                    blob_list.append(blob['name'])
            return blob_list
        except Exception as exc:
            err="Error listing blobs in container"
            raise Exception(err)
    
