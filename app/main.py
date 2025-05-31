from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from pathlib import Path
import uuid
from typing import List

from .services.xml_processor import extract_xml_data
from .services.docx_processor import extract_docx_content
from .services.template_processor import fill_template

# Criar instância do FastAPI
app = FastAPI(
    title="API de Processamento de Documentos",
    description="API para processar arquivos DOCX e XML",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Criar diretórios se não existirem
os.makedirs("uploads", exist_ok=True)
os.makedirs("output", exist_ok=True)
os.makedirs("templates", exist_ok=True)

@app.get("/")
async def root():
    return {"message": "API de Processamento de Documentos está funcionando!"}

@app.get("/health")
async def health_check():
    return {
        "status": "OK",
        "message": "API está saudável"
    }

@app.post("/api/process-documents")
async def process_documents(
    input_docx: UploadFile = File(..., description="Arquivo DOCX de entrada"),
    input_xml: UploadFile = File(..., description="Arquivo XML com dados"),
    template_docx: UploadFile = File(..., description="Template DOCX a ser preenchido")
):
    """
    Processa documentos DOCX e XML para preencher um template
    """
    
    # Validar tipos de arquivo
    if not input_docx.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="input_docx deve ser um arquivo .docx")
    
    if not input_xml.filename.endswith('.xml'):
        raise HTTPException(status_code=400, detail="input_xml deve ser um arquivo .xml")
    
    if not template_docx.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="template_docx deve ser um arquivo .docx")
    
    # Gerar ID único para esta requisição
    request_id = str(uuid.uuid4())
    
    try:
        # Salvar arquivos temporários
        temp_dir = f"uploads/{request_id}"
        os.makedirs(temp_dir, exist_ok=True)
        
        docx_path = f"{temp_dir}/input.docx"
        xml_path = f"{temp_dir}/input.xml"
        template_path = f"{temp_dir}/template.docx"
        
        # Salvar arquivos
        with open(docx_path, "wb") as f:
            shutil.copyfileobj(input_docx.file, f)
        
        with open(xml_path, "wb") as f:
            shutil.copyfileobj(input_xml.file, f)
        
        with open(template_path, "wb") as f:
            shutil.copyfileobj(template_docx.file, f)
        
        # Processar arquivos
        xml_data = extract_xml_data(xml_path)
        docx_content = extract_docx_content(docx_path)
        output_path = fill_template(template_path, xml_data, docx_content, request_id)
        
        # Limpar arquivos temporários
        shutil.rmtree(temp_dir)
        
        return {
            "success": True,
            "message": "Documento processado com sucesso",
            "download_url": f"/api/download/{request_id}",
            "request_id": request_id
        }
        
    except Exception as e:
        # Limpar em caso de erro
        if os.path.exists(f"uploads/{request_id}"):
            shutil.rmtree(f"uploads/{request_id}")
        
        raise HTTPException(status_code=500, detail=f"Erro ao processar documentos: {str(e)}")

@app.get("/api/download/{request_id}")
async def download_document(request_id: str):
    """
    Download do documento processado
    """
    file_path = f"output/documento-{request_id}.docx"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    
    return FileResponse(
        path=file_path,
        filename=f"documento-processado-{request_id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)