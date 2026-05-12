from fastapi import FastAPI

app = FastAPI()

@app.post("/api/users/create")
def create_user():
    return {"ok": True}

class TransformerRecommender:
    pass

