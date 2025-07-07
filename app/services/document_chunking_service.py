
"""
Serviço de chunking inteligente para processamento de documentos extensos
"""
import logging
import re
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Representa um chunk de documento"""
    content: str
    chunk_id: int
    start_position: int
    end_position: int
    metadata: Dict[str, Any]
    chunk_type: str = "content"  # content, header, footer, etc.

class IntelligentChunkingService:
    """
    Serviço para dividir documentos extensos em chunks inteligentes
    mantendo contexto e estrutura
    """
    
    def __init__(self, max_chunk_size: int = 3000, overlap_size: int = 200):
        """
        Inicializa o serviço de chunking
        
        Args:
            max_chunk_size: Tamanho máximo do chunk em caracteres
            overlap_size: Sobreposição entre chunks para manter contexto
        """
        self.max_chunk_size = max_chunk_size
        self.overlap_size = overlap_size
        
    def chunk_document(
        self, 
        document_text: str, 
        document_type: str = "unknown"
    ) -> List[DocumentChunk]:
        """
        Divide documento em chunks inteligentes
        
        Args:
            document_text: Texto completo do documento
            document_type: Tipo do documento para estratégia específica
            
        Returns:
            Lista de chunks do documento
        """
        if len(document_text) <= self.max_chunk_size:
            return [DocumentChunk(
                content=document_text,
                chunk_id=0,
                start_position=0,
                end_position=len(document_text),
                metadata={"total_chunks": 1, "is_complete": True},
                chunk_type="complete"
            )]
        
        logger.info(f"Dividindo documento de {len(document_text)} caracteres em chunks")
        
        # Detectar estrutura do documento
        structure = self._detect_document_structure(document_text)
        
        # Estratégia baseada no tipo de documento
        if document_type in ["livro", "manual", "relatorio"]:
            chunks = self._chunk_by_sections(document_text, structure)
        else:
            chunks = self._chunk_by_paragraphs(document_text)
        
        # Adicionar metadados e IDs
        for i, chunk in enumerate(chunks):
            chunk.chunk_id = i
            chunk.metadata.update({
                "total_chunks": len(chunks),
                "document_type": document_type,
                "structure_info": structure
            })
        
        logger.info(f"Documento dividido em {len(chunks)} chunks")
        return chunks
    
    def _detect_document_structure(self, text: str) -> Dict[str, Any]:
        """Detecta estrutura do documento (capítulos, seções, etc.)"""
        structure = {
            "has_chapters": False,
            "has_sections": False,
            "has_numbered_lists": False,
            "chapter_markers": [],
            "section_markers": []
        }
        
        # Detectar capítulos
        chapter_patterns = [
            r'(?i)^(capítulo|chapter)\s+\d+',
            r'(?i)^(cap\.?)\s+\d+',
            r'^#+\s+',  # Markdown headers
            r'^\d+\.\s+[A-Z]'  # Numbered sections
        ]
        
        for pattern in chapter_patterns:
            matches = list(re.finditer(pattern, text, re.MULTILINE))
            if matches:
                structure["has_chapters"] = True
                structure["chapter_markers"].extend([m.start() for m in matches])
        
        # Detectar seções
        section_patterns = [
            r'(?i)^(seção|section)\s+\d+',
            r'^\d+\.\d+\s+[A-Z]',
            r'^[A-Z][A-Z\s]+$'  # ALL CAPS titles
        ]
        
        for pattern in section_patterns:
            matches = list(re.finditer(pattern, text, re.MULTILINE))
            if matches:
                structure["has_sections"] = True
                structure["section_markers"].extend([m.start() for m in matches])
        
        return structure
    
    def _chunk_by_sections(self, text: str, structure: Dict[str, Any]) -> List[DocumentChunk]:
        """Divide por seções/capítulos mantendo estrutura lógica"""
        chunks = []
        
        # Usar marcadores de capítulos/seções como pontos de divisão
        markers = sorted(set(structure["chapter_markers"] + structure["section_markers"]))
        
        if not markers:
            return self._chunk_by_paragraphs(text)
        
        # Adicionar início e fim do texto
        markers = [0] + markers + [len(text)]
        
        for i in range(len(markers) - 1):
            start = markers[i]
            end = markers[i + 1]
            section_text = text[start:end].strip()
            
            if len(section_text) <= self.max_chunk_size:
                # Seção cabe em um chunk
                chunks.append(DocumentChunk(
                    content=section_text,
                    chunk_id=0,  # Será atualizado depois
                    start_position=start,
                    end_position=end,
                    metadata={"section_number": i},
                    chunk_type="section"
                ))
            else:
                # Seção muito grande, dividir em sub-chunks
                sub_chunks = self._chunk_by_paragraphs(section_text)
                for j, sub_chunk in enumerate(sub_chunks):
                    sub_chunk.start_position = start + sub_chunk.start_position
                    sub_chunk.end_position = start + sub_chunk.end_position
                    sub_chunk.metadata.update({
                        "section_number": i,
                        "sub_chunk": j
                    })
                    chunks.append(sub_chunk)
        
        return chunks
    
    def _chunk_by_paragraphs(self, text: str) -> List[DocumentChunk]:
        """Divide por parágrafos com sobreposição inteligente"""
        chunks = []
        paragraphs = text.split('\n\n')
        
        current_chunk = ""
        start_pos = 0
        current_start = 0
        
        for i, paragraph in enumerate(paragraphs):
            # Calcular posição do parágrafo no texto original
            para_start = text.find(paragraph, start_pos)
            start_pos = para_start + len(paragraph)
            
            # Verificar se adicionar este parágrafo excederia o limite
            potential_chunk = current_chunk + "\n\n" + paragraph if current_chunk else paragraph
            
            if len(potential_chunk) <= self.max_chunk_size:
                current_chunk = potential_chunk
            else:
                # Salvar chunk atual se não estiver vazio
                if current_chunk:
                    chunks.append(DocumentChunk(
                        content=current_chunk.strip(),
                        chunk_id=0,  # Será atualizado depois
                        start_position=current_start,
                        end_position=current_start + len(current_chunk),
                        metadata={"paragraphs": i},
                        chunk_type="paragraphs"
                    ))
                
                # Iniciar novo chunk
                current_chunk = paragraph
                current_start = para_start
        
        # Adicionar último chunk
        if current_chunk:
            chunks.append(DocumentChunk(
                content=current_chunk.strip(),
                chunk_id=0,
                start_position=current_start,
                end_position=current_start + len(current_chunk),
                metadata={"paragraphs": len(paragraphs)},
                chunk_type="paragraphs"
            ))
        
        # Adicionar sobreposição entre chunks
        self._add_overlap(chunks, text)
        
        return chunks
    
    def _add_overlap(self, chunks: List[DocumentChunk], original_text: str):
        """Adiciona sobreposição entre chunks para manter contexto"""
        for i in range(len(chunks) - 1):
            current_chunk = chunks[i]
            next_chunk = chunks[i + 1]
            
            # Adicionar final do chunk atual ao início do próximo
            overlap_start = max(0, current_chunk.end_position - self.overlap_size)
            overlap_text = original_text[overlap_start:current_chunk.end_position]
            
            next_chunk.content = overlap_text + "\n...\n" + next_chunk.content
            next_chunk.metadata["has_overlap"] = True
            next_chunk.metadata["overlap_size"] = len(overlap_text)
    
    def merge_chunk_results(
        self, 
        chunk_results: List[Tuple[DocumentChunk, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Combina resultados de múltiplos chunks em resultado consolidado
        
        Args:
            chunk_results: Lista de tuplas (chunk, resultado_processamento)
            
        Returns:
            Resultado consolidado
        """
        merged_result = {
            "document_type": "unknown",
            "extracted_data": {},
            "all_chunks": [],
            "total_chunks": len(chunk_results),
            "processing_metadata": {
                "chunks_processed": 0,
                "total_characters": 0,
                "confidence_scores": []
            }
        }
        
        for chunk, result in chunk_results:
            merged_result["all_chunks"].append({
                "chunk_id": chunk.chunk_id,
                "content_preview": chunk.content[:100] + "...",
                "result": result
            })
            
            # Consolidar tipo de documento (pegar o mais confiante)
            if "document_type" in result:
                merged_result["document_type"] = result["document_type"]
            
            # Mergear dados extraídos
            if "extracted_data" in result:
                for key, value in result["extracted_data"].items():
                    if key not in merged_result["extracted_data"]:
                        merged_result["extracted_data"][key] = []
                    
                    if isinstance(value, list):
                        merged_result["extracted_data"][key].extend(value)
                    else:
                        merged_result["extracted_data"][key].append(value)
            
            # Atualizar metadados
            merged_result["processing_metadata"]["chunks_processed"] += 1
            merged_result["processing_metadata"]["total_characters"] += len(chunk.content)
            
            if "confidence" in result:
                merged_result["processing_metadata"]["confidence_scores"].append(result["confidence"])
        
        # Calcular confiança média
        if merged_result["processing_metadata"]["confidence_scores"]:
            avg_confidence = sum(merged_result["processing_metadata"]["confidence_scores"]) / len(merged_result["processing_metadata"]["confidence_scores"])
            merged_result["processing_metadata"]["average_confidence"] = avg_confidence
        
        return merged_result
