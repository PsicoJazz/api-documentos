import xml.etree.ElementTree as ET
from typing import Dict, List, Any


def extract_xml_data(xml_path: str) -> Dict[str, Any]:
    """
    Extrai dados do arquivo XML
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Exemplo de extração - adapte conforme sua estrutura XML
        data = {
            "cliente": "",
            "data": "",
            "valores": {},
            "items": []
        }

        # Buscar dados específicos (adapte conforme seu XML)
        for elem in root.iter():
            if elem.tag == "cliente":
                data["cliente"] = elem.text or ""
            elif elem.tag == "data":
                data["data"] = elem.text or ""
            elif elem.tag == "valor":
                data["valores"][elem.get("tipo", "default")] = elem.text or ""

        # Buscar items/lista (exemplo)
        items = root.findall(".//item")
        for item in items:
            item_data = {}
            for child in item:
                item_data[child.tag] = child.text or ""
            data["items"].append(item_data)

        return data

    except Exception as e:
        raise Exception(f"Erro ao processar XML: {str(e)}")
