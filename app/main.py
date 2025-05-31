from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from pathlib import Path
import uuid
from typing import Dict, Any

# Importar serviços (com tratamento de erro)
try:
    from .services.xml_processor import extract_xml_data
    from .services.docx_processor import extract_docx_content
    from .services.template_processor import fill_template
except ImportError:
    # Para execução direta (sem ser módulo)
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from services.xml_processor import extract_xml_data
    from services.docx_processor import extract_docx_content
    from services.template_processor import fill_template

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


def create_directories():
    directories = ["uploads", "output", "templates"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)


# Chamar na inicialização
create_directories()


@app.get("/")
async def root():
    return {
        "message": "API de Processamento de Documentos está funcionando!",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "OK",
        "message": "API está saudável",
        "directories": {
            "uploads": os.path.exists("uploads"),
            "output": os.path.exists("output"),
            "templates": os.path.exists("templates")
        }
    }


def validate_file_extension(filename: str, allowed_extensions: list) -> bool:
    """Valida a extensão do arquivo"""
    if not filename:
        return False
    extension = filename.lower().split('.')[-1]
    return f".{extension}" in allowed_extensions


@app.post("/api/process-documents")
async def process_documents(
    input_docx: UploadFile = File(..., description="Arquivo DOCX de entrada"),
    input_xml: UploadFile = File(..., description="Arquivo XML com dados"),
    template_docx: UploadFile = File(...,
                                     description="Template DOCX a ser preenchido")
):
    """
    Processa documentos DOCX e XML para preencher um template
    """

    # Validar tipos de arquivo
    if not validate_file_extension(input_docx.filename, ['.docx']):
        raise HTTPException(
            status_code=400, detail="input_docx deve ser um arquivo .docx")

    if not validate_file_extension(input_xml.filename, ['.xml']):
        raise HTTPException(
            status_code=400, detail="input_xml deve ser um arquivo .xml")

    if not validate_file_extension(template_docx.filename, ['.docx']):
        raise HTTPException(
            status_code=400, detail="template_docx deve ser um arquivo .docx")

    # Gerar ID único para esta requisição
    request_id = str(uuid.uuid4())
    temp_dir = f"uploads/{request_id}"

    try:
        # Criar diretório temporário
        os.makedirs(temp_dir, exist_ok=True)

        # Definir caminhos dos arquivos
        docx_path = os.path.join(temp_dir, "input.docx")
        xml_path = os.path.join(temp_dir, "input.xml")
        template_path = os.path.join(temp_dir, "template.docx")

        # Salvar arquivos temporários
        with open(docx_path, "wb") as f:
            content = await input_docx.read()
            f.write(content)

        with open(xml_path, "wb") as f:
            content = await input_xml.read()
            f.write(content)

        with open(template_path, "wb") as f:
            content = await template_docx.read()
            f.write(content)

        # Processar arquivos
        xml_data = extract_xml_data(xml_path)
        docx_content = extract_docx_content(docx_path)
        output_path = fill_template(
            template_path, xml_data, docx_content, request_id)

        # Limpar arquivos temporários
        shutil.rmtree(temp_dir, ignore_errors=True)

        return {
            "success": True,
            "message": "Documento processado com sucesso",
            "download_url": f"/api/download/{request_id}",
            "request_id": request_id,
            "processed_data": {
                "xml_data_preview": str(xml_data)[:200] + "..." if len(str(xml_data)) > 200 else str(xml_data),
                "docx_content_preview": docx_content.get("full_text", "")[:200] + "..." if len(docx_content.get("full_text", "")) > 200 else docx_content.get("full_text", "")
            }
        }

    except Exception as e:
        # Limpar em caso de erro
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Erro ao processar documentos",
                "message": str(e),
                "request_id": request_id
            }
        )


@app.get("/api/download/{request_id}")
async def download_document(request_id: str):
    """
    Download do documento processado
    """
    file_path = f"output/documento-{request_id}.docx"

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Arquivo não encontrado",
                "request_id": request_id,
                "file_path": file_path
            }
        )

    return FileResponse(
        path=file_path,
        filename=f"documento-processado-{request_id}.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# Para execução direta
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
