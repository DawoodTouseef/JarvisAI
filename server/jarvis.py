from tkinter import NO
from openai import OpenAI



class AudioLoop:
    def __init__(self,api_key:str=None,base_url:str=None) -> None:
        self.client = OpenAI(api_key=api_key,base_url=base_url)

    