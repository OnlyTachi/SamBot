# Brain/Memory/DataManager/_cache.py


class DataCache:
    """
    Gerencia o armazenamento temporário em memória (RAM) para o DataManager.
    """

    def __init__(self):
        self.data = {}
        self.reset()

    def reset(self):
        self.data = {
            "identity": None,
            "prompts": {},
            "nlp": None,
            "expressions": None,
            "channels": None,
        }

    def get(self, key: str):
        return self.data.get(key)

    def set(self, key: str, value: any):
        self.data[key] = value

    def get_prompt(self, filename: str):
        return self.data["prompts"].get(filename)

    def set_prompt(self, filename: str, content: str):
        self.data["prompts"][filename] = content
