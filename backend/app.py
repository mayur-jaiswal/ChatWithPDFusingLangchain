from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models import Base, Document
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import extract_text_from_pdf
from pydantic import BaseModel
from langchain.llms import LlamaCpp  
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

class QuestionRequest(BaseModel):
    question: str

DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust this as necessary
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure the PDF directory exists
os.makedirs('./pdfs', exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/upload/")
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_location = f"./pdfs/{file.filename}"

    try:
        with open(file_location, "wb") as f:
            f.write(file.file.read())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing file: {str(e)}")

    try:
        content = extract_text_from_pdf(file_location)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text from PDF: {str(e)}")

    document = Document(filename=file.filename, content=content)
    db.add(document)

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving document: {str(e)}")

    return {"filename": file.filename}

@app.post("/ask/{doc_id}")
async def ask_question(doc_id: int, request: QuestionRequest, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == doc_id).first()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Initialize Llama model
    llama_model = LlamaCpp(model_name="llama2", temperature=0.7)  # Adjust model name and parameters

    # Create a prompt for the question
    prompt_template = PromptTemplate(
        input_variables=["question", "context"],
        template="Answer the question based on the following context:\n\n{context}\n\nQuestion: {question}\nAnswer:"
    )

    # Create a chain to process the document content and the question
    chain = LLMChain(llm=llama_model, prompt=prompt_template)

    # Run the query with the document content and the user question
    response = chain.run({"question": request.question, "context": document.content})

    return {"answer": response}
