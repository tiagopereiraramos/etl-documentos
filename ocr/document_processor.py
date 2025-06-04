import os
import re
import time
import uuid
import json
import tempfile
import numpy as np
from datetime import datetime
from typing import Dict, Any, Tuple, List, Optional

import cv2
from PIL import Image
from docling.document_converter import DocumentConverter

# Substituir o logger padrão pelo nosso logger unificado
from utils.logging import get_logger
from utils.document_logging import DocumentTracker

# Importações para rastreamento de uso
from utils.azure_tracker import AzureUsageTracker
from utils.llm_tracker import LLMUsageTracker

# Obter um logger configurado para este módulo
logger = get_logger(__name__)

class DocumentProcessor:
    """
    Classe para processamento de documentos, incluindo extração de texto via Docling e/ou Azure.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Inicializa o processador de documentos com configurações opcionais.
        
        Args:
            config: Configurações para ajustar o comportamento do processador
        """
        self.processor_id = str(uuid.uuid4())[:8]
        logger.info(f"Inicializando novo DocumentProcessor ID: {self.processor_id}")
        
        # Configurações com valores padrão
        self.config = {
            "preprocess_images": True,        # Pré-processar imagens para melhorar OCR
            "quality_threshold": 0.4,         # Limite para processamento intensivo
            "max_dimension": 2500,            # Dimensão máxima para redimensionamento
            "postprocess_text": True,         # Habilitar pós-processamento de texto
            "debug_mode": False,              # Modo debug (salva imagens processadas)
            "temp_dir": "/tmp/docling_temp",  # Diretório para arquivos temporários de debug
            "log_level": "INFO",              # Nível de log
            "use_azure": True,                # Usar Azure AI como fallback/alternativa
            "azure_quality_threshold": 0.30,  # Limite para considerar resultado do Azure
            "text_quality_threshold": 30,     # Características esperadas de um texto de qualidade
            "short_line_threshold": 5,        # Threshold para considerar linhas curtas
            "force_azure_for_extensions": ["jpg", "jpeg", "png", "tif", "tiff"],  # Extensões que favorecem Azure
            "image_tag_threshold": 3,         # Número de tags <!-- image --> que indica documento complexo
            "combine_results": True,          # Tentar combinar resultados quando ambos os métodos são usados
            "ocr_language": "pt",             # Idioma padrão para OCR
            "track_usage": True,              # Rastrear uso de recursos e custos
            "valid_char_patterns": {          # Padrões para validação de caracteres
                "default": r'[a-zA-Z0-9áàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ.,;:!?@#$%&*"\'\s\-\[\]\(\)\/\\_+=]+',
                "pt": r'[a-zA-Z0-9áàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ.,;:!?@#$%&*"\'\s\-\[\]\(\)\/\\_+=]+',
                "en": r'[a-zA-Z0-9.,;:!?@#$%&*"\'\s\-\[\]\(\)\/\\_+=]+'
            }
        }
        
        # Atualiza configurações se fornecidas
        if config:
            self.config.update(config)
            
        # Inicializar componentes
        try:
            start_time = time.time()
            self.document_converter = DocumentConverter()
            elapsed = time.time() - start_time
            logger.info(f"DocumentConverter do Docling inicializado em {elapsed:.3f}s")
        except Exception as e:
            logger.error(f"Erro ao inicializar DocumentConverter do Docling: {str(e)}", exc_info=True)
            self.document_converter = None
            
        # Inicializar rastreadores de uso
        try:
            self.azure_tracker = AzureUsageTracker() if self.config["track_usage"] else None
            logger.info(f"Rastreador de uso do Azure inicializado")
        except Exception as e:
            logger.warning(f"Não foi possível inicializar rastreador de uso do Azure: {str(e)}")
            self.azure_tracker = None
            
        try:
            self.llm_tracker = LLMUsageTracker() if self.config["track_usage"] else None
            logger.info(f"Rastreador de uso de LLMs inicializado")
        except Exception as e:
            logger.warning(f"Não foi possível inicializar rastreador de uso de LLMs: {str(e)}")
            self.llm_tracker = None
            
        # Inicializar Azure Document Intelligence (opcional)
        self.azure_client = None
        if self.config["use_azure"]:
            try:
                from azure.ai.documentintelligence import DocumentIntelligenceClient
                from azure.core.credentials import AzureKeyCredential
                from azure.identity import DefaultAzureCredential
                import os
                
                endpoint = os.environ.get("AZURE_ENDPOINT")  # Alterado de AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
                key = os.environ.get("AZURE_KEY") 
                                
                if endpoint and key:
                    self.azure_client = DocumentIntelligenceClient(
                        endpoint=endpoint, 
                        credential=AzureKeyCredential(key)
                    )
                else:
                    # Tenta usar credenciais padrão do Azure
                    try:
                        self.azure_client = DocumentIntelligenceClient(
                            endpoint=endpoint, 
                            credential=DefaultAzureCredential()
                        )
                    except Exception as e:
                        logger.warning(f"Não foi possível autenticar com DefaultAzureCredential: {str(e)}")
                        
                if self.azure_client:
                    logger.info(f"Cliente Azure Document Intelligence inicializado")
                else:
                    logger.warning(f"Azure Document Intelligence não configurado")
            except Exception as e:
                logger.warning(f"Erro ao inicializar Azure Document Intelligence: {str(e)}")
                
        # Indicar que inicialização foi concluída
        init_elapsed = time.time() - (start_time if 'start_time' in locals() else time.time())
        logger.info(f"DocumentProcessor inicializado em {init_elapsed:.3f}s | ID: {self.processor_id}")
    
    def extract_text(self, file_content: bytes, file_extension: str, document_name: str = None) -> str:
        """
        Extrai texto de um documento, usando primeiro o Docling e recorrendo ao Azure
        apenas se a qualidade do texto extraído for insuficiente ou se for detectado
        um documento com muitas tags de imagem.
        
        Args:
            file_content: Conteúdo do arquivo em bytes
            file_extension: Extensão do arquivo
            document_name: Nome do documento para rastreamento (opcional)
            
        Returns:
            Texto extraído do documento
        """
        doc_id = str(uuid.uuid4())[:6]  # ID único para rastrear este documento específico
        overall_start_time = time.time()
        file_size_kb = len(file_content) / 1024
        doc_name = document_name or f"documento-{doc_id}.{file_extension}"
        
        # Log de início com DocumentTracker
        DocumentTracker.log_processing_start(doc_id, doc_name, file_extension)
        
        logger.info(f"Iniciando extração de texto | ID: {doc_id} | Arquivo: {doc_name} | Tamanho: {file_size_kb:.1f}KB")
        
        temp_path = None
        processed_path = None
        
        try:
            # Detectar tipo real e qualidade
            detect_start_time = time.time()
            doc_type, quality_score = self.detect_document_type(file_content, file_extension)
            detect_elapsed = time.time() - detect_start_time
            
            # Criar arquivo temporário
            with tempfile.NamedTemporaryFile(suffix=f".{file_extension}", delete=False) as temp_file:
                temp_path = temp_file.name
                temp_file.write(file_content)
            
            logger.debug(f"Arquivo temporário criado: {temp_path}")
            
            processed_path = temp_path
            
            # Estratégia específica para imagens
            if doc_type == 'image' and self.config["preprocess_images"]:
                preprocess_start_time = time.time()
                processed_path = self._preprocess_image(temp_path, quality_score, doc_id)
                preprocess_elapsed = time.time() - preprocess_start_time
                logger.info(f"Pré-processamento de imagem concluído em {preprocess_elapsed:.3f}s")
            
            # Decidir se deve usar Azure diretamente (sem tentar Docling)
            use_docling_first = True
            
            # Exceções: casos onde é melhor ir direto para o Azure
            if file_extension.lower() in self.config["force_azure_for_extensions"]:
                if self.azure_client:
                    reason = f"Extensão prioritária para Azure (.{file_extension})"
                    logger.info(f"Priorizando Azure devido à {reason}")
                    use_docling_first = False
                    
                    # Log visual de decisão de usar Azure direto
                    DocumentTracker.log_azure_processing(doc_id, doc_name, "Document Intelligence", reason)
                else:
                    logger.warning(f"Azure seria preferível mas não está disponível")
            
            extracted_text = ""
            
            # 1. Tentar extração com Docling primeiro (na maioria dos casos)
            if use_docling_first:
                try:
                    # Log de processamento Docling
                    DocumentTracker.log_docling_processing(doc_id, doc_name, "Docling Converter", doc_type)
                    
                    # Converter documento usando Docling
                    docling_start_time = time.time()
                    logger.info(f"Iniciando conversão com Docling | ID: {doc_id}")
                    document = self.document_converter.convert(processed_path)
                    docling_convert_elapsed = time.time() - docling_start_time
                    
                    # Extrair texto em markdown
                    docling_extract_start = time.time()
                    docling_text = document.document.export_to_markdown()
                    docling_extract_elapsed = time.time() - docling_extract_start
                    
                    # Avaliar resultado do Docling
                    docling_stats = {
                        "caracteres": len(docling_text) if docling_text else 0,
                        "linhas": docling_text.count('\n') + 1 if docling_text else 0,
                        "tempo_conversao": f"{docling_convert_elapsed:.3f}s",
                        "tempo_extracao": f"{docling_extract_elapsed:.3f}s"
                    }
                    
                    # LOG DEBUG: Amostra do texto extraído
                    if docling_text and len(docling_text) > 0:
                        logger.debug(f"AMOSTRA DOCLING: {docling_text[:200]}...")
                    
                    if not docling_text or len(docling_text.strip()) == 0:
                        logger.warning(f"Docling não extraiu texto útil | ID: {doc_id}")
                        
                        # Tentar extrair texto de páginas individuais
                        if hasattr(document, 'pages'):
                            logger.debug(f"Tentando extrair texto de {len(document.pages)} páginas individuais | ID: {doc_id}")
                            page_texts = []
                            
                            for i, page in enumerate(document.pages):
                                if hasattr(page, 'text'):
                                    page_text = page.text
                                    if page_text:
                                        logger.debug(f"Extraída página {i+1} com {len(page_text)} caracteres")
                                        page_texts.append(page_text)
                            
                            if page_texts:
                                docling_text = "\n\n".join(page_texts)
                                logger.info(f"Extraído texto de {len(page_texts)} páginas com Docling | ID: {doc_id}")
                    else:
                        logger.info(f"Docling extraiu texto com sucesso: {docling_stats['caracteres']} caracteres, {docling_stats['linhas']} linhas")
                    
                    # Se o Docling extraiu texto, avaliar a qualidade
                    use_azure = False
                    if docling_text and len(docling_text.strip()) > 0:
                        # Detectar muitos blocos de imagem (tags)
                        image_tag_count = docling_text.count('<!-- image -->')
                        image_tag_threshold = self.config.get("image_tag_threshold", 3)
                        
                        # Calcular proporção de imagens vs. comprimento do documento
                        total_chars = len(docling_text.strip())
                        
                        # Verificar se excede threshold
                        if image_tag_count >= image_tag_threshold:
                            logger.info(f"Detectadas {image_tag_count} tags de imagem | ID: {doc_id}")
                            
                            if self.azure_client:
                                reason = f"Alta quantidade de áreas não extraídas ({image_tag_count} tags de imagem)"
                                logger.info(f"Direcionando para Azure devido à {reason}")
                                
                                # Log de fallback para Azure
                                DocumentTracker.log_fallback(doc_id, doc_name, "Docling", "Azure", reason)
                                
                                use_azure = True
                                docling_quality = 0.3  # Forçar qualidade baixa para garantir uso do Azure
                            else:
                                logger.warning(f"Documento com muitas áreas não extraídas, mas Azure não disponível")
                                docling_quality = self._evaluate_text_quality(docling_text, doc_id)
                                extracted_text = docling_text  # Usar Docling mesmo assim
                                
                                # Log de resultado com qualidade
                                DocumentTracker.log_extraction_result(doc_id, doc_name, extracted_text, "Docling", docling_quality)
                        else:
                            # Avaliação normal de qualidade
                            docling_quality = self._evaluate_text_quality(docling_text, doc_id)
                            
                            # Log de qualidade avaliada
                            docling_metrics = {
                                "caracteres": len(docling_text),
                                "linhas": docling_text.count('\n') + 1,
                                "image_tags": image_tag_count
                            }
                            DocumentTracker.log_extraction_quality(doc_id, doc_name, docling_quality, docling_metrics, "Docling")
                            
                            # Usar Azure apenas se a qualidade for baixa
                            if docling_quality < 0.4 and self.azure_client:
                                reason = f"Qualidade do texto Docling é baixa ({docling_quality:.2f})"
                                logger.info(f"{reason}. Acionando Azure | ID: {doc_id}")
                                
                                # Log de fallback para Azure
                                DocumentTracker.log_fallback(doc_id, doc_name, "Docling", "Azure", reason)
                                
                                use_azure = True
                            else:
                                extracted_text = docling_text
                                logger.info(f"Usando resultado do Docling (qualidade: {docling_quality:.2f}) | ID: {doc_id}")
                                
                                # Log de resultado com qualidade
                                DocumentTracker.log_extraction_result(doc_id, doc_name, extracted_text, "Docling", docling_quality)
                    else:
                        # Docling não extraiu nada útil
                        use_azure = self.azure_client is not None
                        reason = "Docling não extraiu texto útil"
                        logger.info(f"{reason}. {'Acionando Azure.' if use_azure else 'Azure não disponível.'} | ID: {doc_id}")
                        
                        if use_azure:
                            # Log de fallback para Azure
                            DocumentTracker.log_fallback(doc_id, doc_name, "Docling", "Azure", reason)
                        
                except Exception as e:
                    docling_elapsed = time.time() - docling_start_time if 'docling_start_time' in locals() else 0
                    error_msg = f"Erro ao converter com Docling: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    
                    # Log de erro
                    DocumentTracker.log_error(doc_id, doc_name, error_msg, docling_elapsed)
                    
                    # Tentar Azure em caso de erro no Docling
                    use_azure = self.azure_client is not None
                    if use_azure:
                        reason = f"Falha no processamento Docling: {str(e)}"
                        logger.info(f"Falha no Docling, acionando Azure | ID: {doc_id}")
                        
                        # Log de fallback para Azure
                        DocumentTracker.log_fallback(doc_id, doc_name, "Docling", "Azure", reason)
            else:
                # Decidido pular Docling e ir direto para Azure
                use_azure = self.azure_client is not None
                logger.info(f"Pulando Docling conforme configuração | ID: {doc_id}")
            
            # 2. Usar Azure apenas se necessário (qualidade do Docling baixa, Docling falhou, ou configuração específica)
            if use_azure and self.azure_client:
                try:
                    # Log de processamento Azure
                    DocumentTracker.log_azure_processing(doc_id, doc_name, "Document Intelligence")
                    
                    # Extrair com Azure
                    azure_start_time = time.time()
                    azure_text = self._extract_with_azure(processed_path, doc_id)
                    azure_elapsed = time.time() - azure_start_time
                    
                    if not azure_text:
                        logger.warning(f"Azure não conseguiu extrair texto | ID: {doc_id}")
                        
                        # Log de erro Azure
                        DocumentTracker.log_error(doc_id, doc_name, "Azure não conseguiu extrair texto", azure_elapsed)
                        
                        # Se Azure falhou e temos texto do Docling, mantemos o Docling
                        if not extracted_text:
                            logger.warning(f"Ambos os métodos falharam. Retornando texto vazio | ID: {doc_id}")
                    else:
                        # LOG DEBUG: Amostra do texto extraído
                        logger.debug(f"AMOSTRA AZURE: {azure_text[:200]}...")
                        
                        azure_quality = self._evaluate_text_quality(azure_text, doc_id + "-azure")
                        logger.info(f"Azure extraiu {len(azure_text)} caracteres em {azure_elapsed:.3f}s (qualidade: {azure_quality:.2f}) | ID: {doc_id}")
                        
                        # Log de qualidade Azure
                        azure_metrics = {
                            "caracteres": len(azure_text),
                            "linhas": azure_text.count('\n') + 1,
                            "tempo_processamento": f"{azure_elapsed:.3f}s"
                        }
                        DocumentTracker.log_extraction_quality(doc_id, doc_name, azure_quality, azure_metrics, "Azure")
                        
                        # Usar o texto do Azure se chegamos até aqui (o motivo já foi decidido antes)
                        extracted_text = azure_text
                        logger.info(f"Usando resultado do Azure | ID: {doc_id}")
                        
                        # Log de resultado com qualidade
                        DocumentTracker.log_extraction_result(doc_id, doc_name, extracted_text, "Azure", azure_quality)
                        
                except Exception as e:
                    azure_elapsed = time.time() - azure_start_time if 'azure_start_time' in locals() else 0
                    error_msg = f"Erro ao extrair com Azure: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    
                    # Log de erro
                    DocumentTracker.log_error(doc_id, doc_name, error_msg, azure_elapsed)
            
            # 3. Pós-processar o texto final
            if extracted_text and self.config["postprocess_text"]:
                postprocess_start_time = time.time()
                extracted_text = self._postprocess_text(extracted_text, doc_type, doc_id)
                postprocess_elapsed = time.time() - postprocess_start_time
                logger.debug(f"Pós-processamento concluído em {postprocess_elapsed:.3f}s | ID: {doc_id}")
            
            # 4. Finalizar processamento
            total_elapsed = time.time() - overall_start_time
            success_metrics = {
                "tempo_total": f"{total_elapsed:.3f}s",
                "tamanho_arquivo": f"{file_size_kb:.1f}KB",
                "tipo_documento": doc_type,
                "qualidade_detectada": f"{quality_score:.2f}",
                "texto_extraido_chars": len(extracted_text) if extracted_text else 0,
                "texto_extraido_linhas": extracted_text.count('\n') + 1 if extracted_text else 0,
                "metodo_principal": "Azure" if use_azure and extracted_text else "Docling" if extracted_text else "Nenhum"
            }
            
            logger.info(f"Extração concluída em {total_elapsed:.3f}s | ID: {doc_id}")
            
            # Log de conclusão
            method = success_metrics["metodo_principal"]
            DocumentTracker.log_processing_complete(doc_id, doc_name, total_elapsed, method, success_metrics)
            
            return extracted_text or ""
                
        except Exception as e:
            elapsed = time.time() - overall_start_time
            error_msg = f"Erro crítico na extração de texto: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Log de erro
            DocumentTracker.log_error(doc_id, doc_name, error_msg, elapsed)
            raise
            
        finally:
            # Limpar arquivos temporários
            try:
                if temp_path and os.path.exists(temp_path):
                    os.unlink(temp_path)
                    logger.debug(f"Arquivo temporário removido: {temp_path}")
                    
                if processed_path and processed_path != temp_path and os.path.exists(processed_path):
                    if not self.config["debug_mode"]:
                        os.unlink(processed_path)
                        logger.debug(f"Arquivo processado removido: {processed_path}")
                    else:
                        logger.debug(f"Arquivo processado mantido (debug_mode=True): {processed_path}")
            except Exception as e:
                logger.warning(f"Erro ao limpar arquivos temporários: {str(e)}")

    def _evaluate_text_quality(self, text: str, doc_id: str) -> float:
        """
        Avalia a qualidade do texto extraído para determinar se é aceitável.
        
        Args:
            text: Texto extraído
            doc_id: ID do documento para rastreamento
            
        Returns:
            Pontuação de qualidade entre 0.0 e 1.0
        """
        if not text or len(text.strip()) == 0:
            logger.warning(f"Texto extraído está vazio | ID: {doc_id}")
            return 0.0
            
        # 1. Calcular estatísticas básicas
        total_chars = len(text)
        total_lines = text.count('\n') + 1
        chars_per_line = total_chars / total_lines if total_lines > 0 else 0
        words = text.split()
        total_words = len(words)
        words_per_line = total_words / total_lines if total_lines > 0 else 0
        
        # 2. Calcular proporção de caracteres reconhecíveis vs. "lixo"
        # Obter o padrão de caracteres válidos da configuração
        language = self.config.get("ocr_language", "default")
        valid_chars_pattern = self.config.get("valid_char_patterns", {}).get(
            language, 
            r'[a-zA-Z0-9áàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ.,;:!?@#$%&*"\'\s\-\[\]\(\)\/\\_+=]+'
        )
        
        # Contagem de caracteres válidos
        valid_chars_count = 0
        pattern = re.compile(valid_chars_pattern)
        for char in text:
            if pattern.match(char):
                valid_chars_count += 1
        
        valid_chars_ratio = valid_chars_count / total_chars if total_chars > 0 else 0
        
        # 3. Verificar estrutura (linhas muito curtas são sinal de problema)
        short_line_threshold = self.config.get("short_line_threshold", 5)
        short_lines = len([line for line in text.splitlines() if len(line.strip()) < short_line_threshold])
        short_line_ratio = short_lines / total_lines if total_lines > 0 else 1.0
        
        # 4. Verificar palavras reconhecíveis vs. sequências aleatórias
        valid_word_pattern = r'^[a-zA-Z0-9áàâãéèêíìîóòôõúùûçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÇ]+$'
        valid_words = len([word for word in words if len(word) > 1 and re.match(valid_word_pattern, word)])
        valid_word_ratio = valid_words / total_words if total_words > 0 else 0
        
        # 5. Calcular pontuação composta
        text_quality_threshold = min(30, self.config.get("text_quality_threshold", 30))
        quality_score = (
            0.3 * min(1.0, chars_per_line / text_quality_threshold) +
            0.4 * valid_chars_ratio +
            0.2 * (1.0 - short_line_ratio) +
            0.1 * valid_word_ratio
        )
        
        # Garantir que a qualidade nunca seja menos que 0.4 para PDFs com camada de texto
        pdf_text_layer_boost = 0.0
        if hasattr(self, 'last_doc_had_text_layer') and self.last_doc_had_text_layer and quality_score < 0.4:
            pdf_text_layer_boost = 0.2
            quality_score = max(quality_score, 0.4)  # PDF com texto sempre tem pelo menos 0.4
        
        metrics = {
            "caracteres_totais": total_chars,
            "linhas_totais": total_lines,
            "chars_por_linha": f"{chars_per_line:.1f}",
            "palavras_totais": total_words,
            "palavras_por_linha": f"{words_per_line:.1f}",
            "prop_chars_validos": f"{valid_chars_ratio:.2f}",
            "prop_linhas_curtas": f"{short_line_ratio:.2f}",
            "prop_palavras_validas": f"{valid_word_ratio:.2f}",
            "pdf_text_boost": f"{pdf_text_layer_boost:.2f}" if pdf_text_layer_boost > 0 else "0.00",
            "qualidade_texto": f"{quality_score:.2f}"
        }
        
        logger.info(f"Análise de qualidade do texto | ID: {doc_id} | Qualidade: {quality_score:.2f}")
        logger.debug(f"Métricas detalhadas: {json.dumps(metrics)}")
        
        return quality_score
        
    def detect_document_type(self, file_content: bytes, file_extension: str) -> Tuple[str, float]:
        """
        Detecta o tipo real do documento e avalia sua qualidade inicial.
        
        Args:
            file_content: Conteúdo do arquivo em bytes
            file_extension: Extensão do arquivo
            
        Returns:
            Tupla com tipo do documento e pontuação de qualidade
        """
        doc_id = str(uuid.uuid4())[:6]  # ID para rastreamento nos logs
        logger.info(f"Analisando documento | ID: {doc_id} | Extensão: {file_extension} | Tamanho: {len(file_content)/1024:.1f}KB")
        
        start_time = time.time()
        doc_type = file_extension.lower()
        quality_score = 0.5  # Valor padrão
        
        if file_extension.lower() == 'pdf':
            try:
                import pikepdf
                
                # Criar arquivo temporário para análise
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                    temp_file.write(file_content)
                    temp_path = temp_file.name
                
                try:
                    # Detectar se tem camada de texto
                    pdf = pikepdf.Pdf.open(temp_path)
                    has_text = False
                    page_count = len(pdf.pages)
                    
                    for i, page in enumerate(pdf.pages):
                        if '/Contents' in page and '/Resources' in page:
                            resources = page['/Resources']
                            if '/Font' in resources:
                                has_text = True
                                break
                    
                    if has_text:
                        quality_score = 0.75  # PDFs com texto são geralmente melhores
                        logger.info(f"PDF com camada de texto detectado | ID: {doc_id} | Qualidade: {quality_score}")
                    else:
                        quality_score = 0.4
                        logger.info(f"PDF sem texto detectado (possivelmente escaneado) | ID: {doc_id} | Qualidade: {quality_score}")
                        
                finally:
                    # Limpar
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                
            except Exception as e:
                logger.warning(f"Erro ao analisar PDF: {str(e)} | ID: {doc_id}")
                quality_score = 0.4  # Se não conseguiu analisar, assume pior caso
                
        elif file_extension.lower() in ['jpg', 'jpeg', 'png', 'tiff', 'tif', 'bmp', 'webp']:
            doc_type = 'image'
            
            try:
                # Análise básica da imagem
                with tempfile.NamedTemporaryFile(suffix=f".{file_extension}", delete=False) as temp_file:
                    temp_file.write(file_content)
                    temp_path = temp_file.name
                
                try:
                    # Abrir com PIL para análise
                    img = Image.open(temp_path)
                    width, height = img.size
                    
                    # Avaliar qualidade baseada no tamanho
                    size_factor = min(1.0, (width * height) / (1200 * 1600)) * 0.3
                    
                    # Se muito pequena, qualidade baixa
                    if width < 600 or height < 800:
                        quality_score = 0.3
                    # Se tamanho bom, qualidade média-alta
                    else:
                        quality_score = 0.5 + size_factor
                        
                    logger.info(f"Imagem analisada | ID: {doc_id} | Dimensões: {width}x{height} | Qualidade: {quality_score:.2f}")
                    
                finally:
                    # Limpar
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                        
            except Exception as e:
                logger.warning(f"Erro ao analisar imagem: {str(e)} | ID: {doc_id}")
                quality_score = 0.4
                
        elif file_extension.lower() in ['docx', 'xlsx', 'pptx', 'txt', 'rtf', 'odt']:
            quality_score = 0.8  # Formatos com texto nativo geralmente têm alta qualidade
            logger.info(f"Documento com formato textual nativo | ID: {doc_id} | Qualidade: {quality_score}")
            
        else:
            # Formato não comum, usar valor padrão
            quality_score = 0.5
            logger.info(f"Formato não comum (.{file_extension}) | ID: {doc_id} | Qualidade padrão: {quality_score}")
            
        elapsed = time.time() - start_time
        logger.info(f"Documento analisado em {elapsed:.3f}s | ID: {doc_id} | Tipo: {doc_type} | Qualidade: {quality_score}")
        
        # Armazenar informação se o PDF tem camada de texto para uso posterior
        if doc_type == 'pdf' and 'has_text' in locals():
            self.last_doc_had_text_layer = has_text
        else:
            self.last_doc_had_text_layer = False
            
        return doc_type, quality_score

    def _extract_with_azure(self, file_path: str, doc_id: str) -> str:
        """
        Extrai texto de um documento usando Azure Document Intelligence.
        """
        if not self.azure_client:
            logger.warning(f"Azure Document Intelligence não configurado | ID: {doc_id}")
            return ""
            
        start_time = time.time()
        logger.info(f"Iniciando extração com Azure | ID: {doc_id}")
        
        try:
            with open(file_path, "rb") as f:
                document_bytes = f.read()
                
            # Rastrear uso se habilitado
            if self.azure_tracker:
                self.azure_tracker.record_usage(
                    document_id=doc_id,
                    model="prebuilt-layout",
                    pages=1,  # Provisório
                    size_bytes=len(document_bytes),
                    success=True,
                    metadata={"operation": "document_intelligence"}
                )
            
            # Enviar documento para Azure
            poller = self.azure_client.begin_analyze_document(
                "prebuilt-layout",
                body=document_bytes
            )
            result = poller.result()
            
            # Extrair texto de todas as páginas
            all_text = []
            page_count = len(result.pages) if hasattr(result, 'pages') else 0
            
            for page in result.pages:
                page_lines = []
                for line in page.lines:
                    page_lines.append(line.content)
                page_text = "\n".join(page_lines)
                all_text.append(page_text)
                
            combined_text = "\n\n".join(all_text)
            elapsed = time.time() - start_time
            
            # Atualizar uso com contagem real de páginas
            if self.azure_tracker and page_count > 1:
                self.azure_tracker.record_usage(
                    document_id=doc_id,
                    model="prebuilt-layout",
                    pages=page_count,
                    size_bytes=len(document_bytes),
                    success=True,
                    metadata={"operation": "document_intelligence"}
                )
            
            # Log do resultado da extração
            DocumentTracker.log_extraction_result(
                doc_id=doc_id, 
                doc_name=os.path.basename(file_path), 
                extracted_text=combined_text, 
                method="Azure",
                quality_score=None
            )
            
            logger.info(f"Extração Azure concluída | ID: {doc_id} | Tempo: {elapsed:.3f}s | Páginas: {page_count} | Caracteres: {len(combined_text)}")
            
            return combined_text
            
        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = f"Erro na extração com Azure: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            # Log de erro
            DocumentTracker.log_error(
                doc_id=doc_id, 
                doc_name=os.path.basename(file_path), 
                error_message=error_msg,
                elapsed_time=elapsed
            )
            
            # Registrar falha
            if self.azure_tracker:
                self.azure_tracker.record_usage(
                    document_id=doc_id,
                    model="prebuilt-layout",
                    pages=0,
                    size_bytes=len(document_bytes) if 'document_bytes' in locals() else 0,
                    success=False,
                    metadata={"error": str(e)}
                )
            
            return ""

    def _preprocess_image(self, image_path: str, quality_score: float, doc_id: str) -> str:
        """
        Pré-processa uma imagem para melhorar resultados de OCR.
        """
        start_time = time.time()
        
        try:
            # Se qualidade já é boa, aplicar processamento mínimo
            if quality_score >= self.config["quality_threshold"]:
                logger.debug(f"Qualidade suficiente, aplicando processamento leve | ID: {doc_id}")
                return self._basic_image_processing(image_path, doc_id)
            else:
                logger.debug(f"Qualidade baixa ({quality_score:.2f}), aplicando processamento intensivo | ID: {doc_id}")
                return self._enhanced_image_processing(image_path, doc_id)
                
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"Erro no pré-processamento de imagem: {str(e)} | ID: {doc_id}", exc_info=True)
            return image_path
            
    def _basic_image_processing(self, image_path: str, doc_id: str) -> str:
        """
        Processamento básico de imagem (redimensionamento, ajuste de contraste).
        """
        img = cv2.imread(image_path)
        if img is None:
            logger.warning(f"Falha ao ler imagem: {image_path} | ID: {doc_id}")
            return image_path
            
        # Redimensionar se muito grande
        height, width = img.shape[:2]
        max_dim = self.config["max_dimension"]
        
        if max(height, width) > max_dim:
            scale = max_dim / max(height, width)
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height))
            logger.debug(f"Imagem redimensionada: {width}x{height} -> {new_width}x{new_height} | ID: {doc_id}")
            
        # Ajuste básico de contraste
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge((l, a, b))
        img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        
        # Salvar resultado
        processed_path = f"{os.path.splitext(image_path)[0]}_proc{os.path.splitext(image_path)[1]}"
        cv2.imwrite(processed_path, img)
        
        return processed_path
        
    def _enhanced_image_processing(self, image_path: str, doc_id: str) -> str:
        """
        Processamento avançado para imagens de baixa qualidade.
        """
        img = cv2.imread(image_path)
        if img is None:
            logger.warning(f"Falha ao ler imagem: {image_path} | ID: {doc_id}")
            return image_path
            
        # Converter para escala de cinza
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Aplicar blur para reduzir ruído
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Detecção de bordas
        edges = cv2.Canny(blurred, 50, 150)
        
        # Dilatação para conectar bordas
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)
        
        # Encontrar contornos
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Se tiver contornos significativos, pode tentar ajustar perspectiva
        if len(contours) > 0 and max([cv2.contourArea(c) for c in contours]) > 10000:
            largest_contour = max(contours, key=cv2.contourArea)
            rect = cv2.minAreaRect(largest_contour)
            box = cv2.boxPoints(rect)
            box = np.int0(box)
            
            # Desenhar contornos principais para debug
            if self.config["debug_mode"]:
                debug_img = img.copy()
                cv2.drawContours(debug_img, [box], 0, (0, 255, 0), 2)
                debug_path = os.path.join(self.config["temp_dir"], f"{os.path.basename(image_path)}_debug_contours.jpg")
                cv2.imwrite(debug_path, debug_img)
                logger.debug(f"Imagem de debug salva: {debug_path} | ID: {doc_id}")
        
        # Binarização adaptativa
        binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
        
        # Salvar resultado
        processed_path = f"{os.path.splitext(image_path)[0]}_proc{os.path.splitext(image_path)[1]}"
        cv2.imwrite(processed_path, binary)
        
        return processed_path
    
    def _postprocess_text(self, text: str, doc_type: str, doc_id: str) -> str:
        """
        Aplica pós-processamento ao texto extraído.
        """
        if not text:
            return text
            
        start_time = time.time()
        original_chars = len(text)
        original_words = len(text.split())
        
        # Remover espaços extras
        text = re.sub(r' +', ' ', text)
        
        # Remover linhas em branco repetidas
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Juntar palavras quebradas
        text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
        
        # Corrigir espaços antes de pontuação
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        
        elapsed = time.time() - start_time
        final_chars = len(text)
        final_words = len(text.split())
        
        logger.debug(
            f"Pós-processamento concluído | ID: {doc_id} | Caracteres: {original_chars} → {final_chars} | "
            f"Palavras: {original_words} → {final_words} | Tempo: {elapsed:.3f}s"
        )
        
        return text