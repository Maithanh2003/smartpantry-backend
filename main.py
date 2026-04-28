from fastapi import FastAPI

app = FastAPI(title="SmartPantry API")

@app.get("/health")
def health():
    return {"status": "ok"}