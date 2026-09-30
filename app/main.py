from fastapi import FastAPI

app = FastAPI(title="WeHelp Message Board")


@app.get("/health")
def health():
    return {"status": "ok"}
